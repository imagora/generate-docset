#!/usr/local/bin/python3
# -- coding: utf-8 --
"""
Author: shanhui@agora.io
"""

import os
import re
import bs4
import sys
import sqlite3


class DocsetGenerator:
    def __init__(self, path):
        self.html_path = path
        self.sqlite_conn = None
        self.sqlite_cur = None
        self.entry_types = {
            'Classes': 'Class',
            'Constants': 'Enum',
            'Protocols': 'Protocol',
        }

    def setup_sqlite(self, sql_path):
        if self.sqlite_conn is not None:
            return True

        self.sqlite_conn = sqlite3.connect(sql_path)
        self.sqlite_cur = self.sqlite_conn.cursor()

        try:
            self.sqlite_cur.execute('DROP TABLE searchIndex;')
        except Exception as e:
            print('drop old database failed', repr(e))

        self.sqlite_cur.execute('CREATE TABLE searchIndex('
                                'id INTEGER PRIMARY KEY, '
                                'name TEXT, '
                                'type TEXT, '
                                'path TEXT);')
        self.sqlite_cur.execute('CREATE UNIQUE INDEX anchor ON '
                                'searchIndex(name, type, path);')
        return True

    def add_entry(self, entry_type, entry_name, entry_path):
        self.sqlite_cur.execute('INSERT OR IGNORE INTO '
                                'searchIndex(name, type, path) VALUES (?,?,?)',
                                (entry_name, entry_type, entry_path))

    def generate_by_file(self, dir_name, html_file):
        entry_type = self.entry_types[dir_name]
        sub_type = 'Attribute'
        if entry_type == 'Enum':
            sub_type = 'Constant'
        print('generate type', entry_type, 'file', html_file)
        self.add_entry(entry_type, html_file.split('.')[0],
                       os.path.join(dir_name, html_file))

        if sub_type == 'Constant':
            return

        absolute_path = os.path.join(self.html_path, dir_name, html_file)
        html_page = open(absolute_path).read()
        soup = bs4.BeautifulSoup(html_page)
        for titles in soup.find_all(attrs={'class': 'method-title'}):
            for code in titles.find_all('code'):
                for tag in code.find_all('a', {'href': re.compile('.*')}):
                    name = tag.text.strip()
                    if not name:
                        continue

                    sub_type = 'Attribute'
                    if '+' in name:
                        sub_type = 'Function'
                    if '–' in name:
                        sub_type = 'Method'
                    path = tag.attrs['href'].strip()
                    if 'index.html' in path:
                        continue
                    self.add_entry(sub_type, name, os.path.join(dir_name, html_file) + path)

    def generate_by_dir(self, dir_name):
        print('generate docset by', dir_name)
        if dir_name not in self.entry_types:
            print('ignore not supported entry type', dir_name)
            return

        for _, _, files in os.walk(os.path.join(self.html_path, dir_name)):
            for html_file in files:
                self.generate_by_file(dir_name, html_file)

    def generate(self):
        if not self.setup_sqlite(os.path.join(self.html_path, 'docSet.dsidx')):
            return

        ignore_dirs = ['css', 'img', 'js', 'docs']
        for _, dirs, _ in os.walk(self.html_path):
            for dir_name in dirs:
                if dir_name in ignore_dirs:
                    continue
                self.generate_by_dir(dir_name)

        self.sqlite_conn.commit()
        self.sqlite_conn.close()


def main():
    if len(sys.argv) < 2:
        print('run as: python3 generate_docset.py html/file/path')
        exit(1)

    html_file_path = sys.argv[1]
    generator = DocsetGenerator(html_file_path)
    generator.generate()
    exit(0)


if __name__ == '__main__':
    main()
