"""

Created by: Nathan Starkweather
Created on: 12/10/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from xml.etree.ElementTree import Element
from io import StringIO


def _simple_xml_dump_inner_unicode_debug(b, elem, level):
    """
    @param b: BytesIO
    @type b: BytesIO
    @param elem: Element
    @type elem: Element
    """
    tag = elem.tag

    b.write("\t" * level)
    b.write(tag.join(("<", ">")))
    if len(elem):
        b.write("\n")
        b.write("\t" * level)

    txt = elem.text
    if txt:
        b.write(txt)
        if len(elem) and txt.strip():
            b.write("\n")
            b.write("\t" * level)

    for e in elem:
        _simple_xml_dump_inner_unicode_debug(b, e, level + 1)

    if len(elem):
        b.write("\t" * level)
    b.write(tag.join(("</", ">\n")))


def simple_xml_dump_debug(root):
    """
    Simple XML tree generator for elements with nothing but
    a tag, text, tail, and children. No attributes supported.

    @param root: Root element for an xml document
    @return: bytes
    """
    b = StringIO()
    b.write('<?xml version="1.0" encoding="utf-8" standalone="no" ?>')
    _simple_xml_dump_inner_unicode_debug(b, root, 0)
    return '\n'.join(filter(str.strip, b.getvalue().splitlines()))

from json import dumps
