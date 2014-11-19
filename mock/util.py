"""

Created by: Nathan Starkweather
Created on: 11/07/2014
Created in: PyCharm Community Edition


"""
from functools import wraps
from xml.etree.ElementTree import tostring as xml_tostring, Element, SubElement

__author__ = 'Nathan Starkweather'


def nextroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        return g.__next__
    return wrapper


def sendroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.send
    return wrapper


def xml_dump(obj, root=None, encoding='us-ascii'):
    if isinstance(obj, dict):
        obj = _dict_toxml(obj, root)
    return xml_tostring(obj, encoding)


from io import BytesIO


def _simple_xml_dump_inner_ascii(b, elem):
    """
    @param b: BytesIO
    @type b: BytesIO
    @param elem: Element
    @type elem: Element
    """
    tag = elem.tag.encode('ascii')
    b.write(tag.join((b"<", b">\n")))

    txt = elem.text
    if txt:
        b.write(txt.encode('ascii') + b"\n")

    for e in elem:
        _simple_xml_dump_inner_ascii(b, e)

    b.write(tag.join((b"</", b">\n")))


def simple_xml_dump(root):
    """
    @param root: Root element for an xml document
    @return:
    """
    b = BytesIO()
    _simple_xml_dump_inner_ascii(b, root)
    return b.getvalue()


def _dict_toxml(mapping, root):
    if root is None:
        root = Element("Reply")
        root.text = "\n"
    for k, v in mapping.items():
        e = SubElement(root, k)
        if isinstance(v, dict):
            _dict_toxml(v, e)
            e.text = '\n'
        else:
            e.text = str(v)
    return root

import inspect


def lineno():
    """
    Easily retrieve the current line number
    """
    return inspect.currentframe().f_back.f_lineno
