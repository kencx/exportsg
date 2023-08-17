#!/usr/bin/env python3

import argparse
import csv
from py_pdf_parser.loaders import load_file
from py_pdf_parser.tables import extract_table, add_header_to_table
from py_pdf_parser.exceptions import NoElementFoundError


class Bank:
    IGNORED = []
    FIRST_ELEMENT = ""
    LAST_PAGE_ELEMENT = ""
    LAST_ELEMENT = ""
    COLUMNS = []

    def __init__(self, path, visualize):
        self.document = load_file(path)
        self.last_page = self.last_page()
        self.ignore_elements()

        self.visualize = visualize
        self.table = self.parse_pdf()

    def last_page(self):
        if self.LAST_ELEMENT != "":
            return (
                self.document.elements.filter_by_text_contains(self.LAST_ELEMENT)
                .extract_single_element()
                .page_number
            )
        else:
            return

    def ignore_elements(self):
        for t in self.IGNORED:
            self.document.elements.filter_by_text_contains(t).ignore_elements()

        if self.LAST_ELEMENT:
            self.document.elements.below(
                self.document.elements.filter_by_text_contains(
                    self.LAST_ELEMENT
                ).extract_single_element(),
                inclusive=False,
                all_pages=True,
            ).ignore_elements()

    def create_page_section(self, page, section_name):
        try:
            elem = page.filter_by_text_equal(
                self.FIRST_ELEMENT
            ).extract_single_element()
        except NoElementFoundError:
            print(f'No "{self.FIRST_ELEMENT}" element found on page, skipping...')
            return

        if self.LAST_ELEMENT != "":
            try:
                final_elem = page.filter_by_text_contains(
                    self.LAST_ELEMENT
                ).extract_single_element()

            except NoElementFoundError:
                try:
                    final_elem = page.filter_by_text_contains(
                        self.LAST_PAGE_ELEMENT
                    ).extract_single_element()
                except NoElementFoundError:
                    print("No footer element found on page, skipping...")
                    return
        else:
            try:
                final_elem = page.filter_by_text_contains(
                    self.LAST_PAGE_ELEMENT
                ).extract_single_element()
            except NoElementFoundError:
                print("No footer element found on page, skipping...")
                return

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

        if self.last_page is not None:
            last = self.last_page
        else:
            last = self.document.number_of_pages

        for i in range(last):
            pages.append(self.document.elements.filter_by_page(i + 1))

        res = []
        for i, p in enumerate(pages):
            section = self.create_page_section(p, f"t{i+1}")
            if section is None:
                continue

            table = self.create_page_table(section)
            res.append(table)

        if len(res) == 0:
            return

        if self.visualize:
            from py_pdf_parser.visualise import visualise

            visualise(self.document)

        return flatten(res)


class POSB(Bank):
    IGNORED = [
        "CURRENCY",
        "SINGAPORE DOLLAR",
        "Balance Brought Forward",
    ]
    FIRST_ELEMENT = "DATE"
    LAST_PAGE_ELEMENT = "Balance Carried Forward"
    LAST_ELEMENT = ""
    COLUMNS = ["DATE", "DESCRIPTION", "WITHDRAWAL", "DEPOSIT", "BALANCE"]

    def __init__(self, path, visualize):
        super().__init__(path, visualize)

    def build_balance_sheet(self):
        table = []

        for line in self.table:
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
                all(col in line for col in self.COLUMNS)
                and line["DATE"] != ""
                and line["DESCRIPTION"] != ""
                and ((line["WITHDRAWAL"] != "") is not (line["DEPOSIT"] != ""))
            ):
                row = line

            if any(row):
                table.append(row)

        table = quote_newlines(table)
        return table


class UOB(Bank):
    IGNORED = [
        "PREVIOUS BALANCE",
    ]
    FIRST_ELEMENT = "Description of Transaction"
    LAST_PAGE_ELEMENT = "Please note"
    LAST_ELEMENT = "End of Transaction Details"
    COLUMNS = [
        "Post\nDate",
        "Trans\nDate",
        "Description of Transaction",
        "Transaction Amount\nSGD",
    ]

    def __init__(self, path, visualize):
        super().__init__(path, visualize)

    def build_balance_sheet(self):
        res = []

        for line in self.table:
            row = {}

            # remove newlines in keys
            for k, v in line.items():
                row[k.replace("\n", " ")] = v

            # keep valid transactions only
            if not (
                all(col in row for col in row.keys())
                and row["Post Date"] != ""
                and row["Trans Date"] != ""
            ):
                continue

            if any(row):
                res.append(row)

        res = quote_newlines(res)
        return res


def flatten(ls):
    return [item for sublist in ls for item in sublist]


def quote_newlines(lst):
    for line in lst:
        # replace all \n with \\n
        for k, v in line.items():
            line[k] = v.replace("\n", "\\n")

    return lst


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-p", "--posb", required=False, type=str, help="POSB statement to parse"
    )
    parser.add_argument(
        "-u", "--uob", required=False, type=str, help="UOB statement to parse"
    )
    parser.add_argument(
        "-f", "--file", required=False, type=str, help="Output file to write"
    )
    parser.add_argument(
        "-v",
        "--visualize",
        required=False,
        action="store_true",
        help="Visualize document",
    )
    args = parser.parse_args()

    if args.posb:
        res = POSB(path=args.posb, visualize=args.visualize)
    elif args.uob:
        res = UOB(path=args.uob, visualize=args.visualize)
    else:
        print("This PDF is not supported")
        exit(1)

    if res.table is None:
        exit(1)
    d = res.build_balance_sheet()

    if args.file is not None and len(d):
        with open(args.file, mode="w") as f:
            writer = csv.DictWriter(f, d[0].keys())
            writer.writeheader()
            writer.writerows(d)
