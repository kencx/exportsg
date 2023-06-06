#!/usr/bin/env python3

import argparse
import csv
from pprint import pprint
from py_pdf_parser.loaders import load_file
from py_pdf_parser.tables import extract_table, add_header_to_table


class POSB:
    IGNORED = [
        "CURRENCY",
        "SINGAPORE DOLLAR",
        "Balance Brought Forward",
    ]

    def __init__(self, path, visualize):
        self.document = load_file(path)
        self.ignore_elements()

        self.visualize = visualize
        self.table = self.parse_pdf()

    def ignore_elements(self):
        for t in self.IGNORED:
            self.document.elements.filter_by_text_contains(t).ignore_elements()

    def create_page_section(self, page, section_name):
        elem = page.filter_by_text_equal("DATE").extract_single_element()
        final_elem = page.filter_by_text_equal(
            "Balance Carried Forward"
        ).extract_single_element()

        section = self.document.sectioning.create_section(
            section_name, elem, final_elem, include_last_element=True
        )
        return section

    def create_page_table(self, section):
        table = extract_table(
            section.elements,
            as_text=True,
            fix_element_in_multiple_cols=True,
            fix_element_in_multiple_rows=True,
        )
        return add_header_to_table(table)

    def parse_pdf(self):
        pages = []
        for i in range(self.document.number_of_pages):
            pages.append(self.document.elements.filter_by_page(i + 1))

        res = []
        for i, p in enumerate(pages):
            section = self.create_page_section(p, f"t{i+1}")
            table = self.create_page_table(section)
            res.append(table)

        if self.visualize:
            from py_pdf_parser.visualise import visualise

            visualise(self.document)

        return flatten(res)


def flatten(ls):
    return [item for sublist in ls for item in sublist]


def quote_newlines(lst):
    for line in lst:
        # replace all \n with \\n
        for k, v in line.items():
            line[k] = v.replace("\n", "\\n")

    return lst


def build_balance_sheet(lst):
    table = []
    columns = ["DATE", "DESCRIPTION", "WITHDRAWAL", "DEPOSIT", "BALANCE"]

    for line in lst:
        row = {}

        # combine relevant transaction descriptions
        if (
            line["DATE"] == ""
            and line["DESCRIPTION"] != ""
            and "DESCRIPTION" in table[-1].keys()
            and line["DESCRIPTION"] not in ["Total", "Balance Carried Forward"]
        ):
            table[-1]["DESCRIPTION"] += "\n" + line["DESCRIPTION"]
            continue

        # keep valid transactions only
        if (
            all(col in line for col in columns)
            and line["DATE"] != ""
            and line["DESCRIPTION"] != ""
            and ((line["WITHDRAWAL"] != "") is not (line["DEPOSIT"] != ""))
        ):
            row = line

        if any(row):
            table.append(row)

    table = quote_newlines(table)
    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-f", "--file", required=True, type=str, help="PDF file to parse"
    )
    parser.add_argument(
        "-o", "--output", required=False, type=str, help="Output file to write"
    )
    parser.add_argument(
        "-v", "--visualize", required=False, type=bool, help="Visualize document"
    )
    args = parser.parse_args()

    res = POSB(path=args.file, visualize=args.visualize)
    d = build_balance_sheet(res.table)
    # pprint(d)

    if args.output is not None:
        with open(args.output, mode="w") as f:
            writer = csv.DictWriter(f, d[0].keys())
            writer.writeheader()
            writer.writerows(d)
