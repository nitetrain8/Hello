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

    """

    Dispatch function to turn a python object into
    an xml string.

    @param obj: python container or xml root object
    @param root: Element instance to act as the root
    """

    if isinstance(obj, dict):
        obj = _dict_toxml(obj, root)
    elif isinstance(obj, Iterable) and not isinstance(obj, str):
        obj = _iter_toxml(root, "Response", obj)
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
    b.write(tag.join((b"<", b">")))

    txt = elem.text
    if txt:
        b.write(txt.encode('ascii'))

    for e in elem:
        _simple_xml_dump_inner_ascii(b, e)

    b.write(tag.join((b"</", b">")))
    tail = elem.tail
    if tail:
        b.write(tail.encode('ascii'))


def _simple_xml_dump_inner_unicode(b, elem):
    """
    @param b: BytesIO
    @type b: BytesIO
    @param elem: Element
    @type elem: Element
    """
    tag = elem.tag
    b.write(tag.join(("<", ">\n")))

    txt = elem.text
    if txt:
        b.write(txt)

    for e in elem:
        _simple_xml_dump_inner_ascii(b, e)

    b.write(tag.join(("</", ">")))
    tail = elem.tail
    if tail:
        b.write(tail)


def simple_xml_dump(root):
    """
    Simple XML tree generator for elements with nothing but
    a tag, text, and maybe children.

    @param root: Root element for an xml document
    @return: bytes
    """
    b = BytesIO()
    b.write(b'<?xml version="1.0" encoding="windows-1252" standalone="no" ?>')
    _simple_xml_dump_inner_ascii(b, root)
    return b.getvalue()


from collections import Iterable, OrderedDict


def _iter_toxml(root, name, lst):

    if not isinstance(lst, (list, tuple)):
        lst = tuple(lst)

    if root is None:
        reply = Element("Reply")
        reply.text = ""
        result = SubElement(reply, "Result")
        result.text = "True"
        message = SubElement(reply, "Message")
        message.text = ""
        root = message

    cluster = SubElement(root, "Cluster")
    name_ele = SubElement(cluster, "Name")
    name_ele.text = name
    nele = SubElement(cluster, "NumElts")
    nele.text = str(len(lst))

    for k, v in lst:
        if isinstance(v, dict):
            e = SubElement(cluster, k)
            _dict_toxml(v, e)
            e.text = '\n'
        elif isinstance(v, Iterable) and not isinstance(v, str):
            _iter_toxml(cluster, k, v)
        else:
            e = SubElement(cluster, k)
            e.text = str(v)
    return root


def _dict_toxml(mapping, root):
    if root is None:
        root = Element("Reply")
        root.text = "\n"
    for k, v in mapping.items():
        if isinstance(v, dict):
            e = SubElement(root, k)
            _dict_toxml(v, e)
            e.text = '\n'
        elif isinstance(v, Iterable) and not isinstance(v, str):
            _iter_toxml(root, k, v)
        else:
            e = SubElement(root, k)
            e.text = str(v)
    return root

import inspect


def lineno(back=1):
    """
    Easily retrieve the current line number
    """
    frame = inspect.currentframe()
    for _ in range(back):
        frame = frame.f_back
    return frame.f_lineno


class HelloXMLGenerator():

    """ Generate server XML responses from python objects.
     Attempt to "naturally" replicate structure format produced
     by labview code, hack when necessary.

     Note that all type conversion functions use the SubElement
      factory function to modify the tree in-place, rather than
      returning values.


    """
    def __init__(self):
        self.parse_types = {
            str: self.str_toxml,
            int: self.int_toxml,
            list: self.list_toxml,
            tuple: self.list_toxml,
            dict: self.dict_toxml,
            float: self.float_toxml,
            OrderedDict: self.dict_toxml,
            type(_ for _ in ""): self.iter_toxml  # generator
        }

    def register(self, typ, parsefunc):
        self.parse_types[typ] = parsefunc

    def dispatch(self, obj, name, root):
        try:
            parse = self.parse_types[type(obj)]
        except KeyError as e:
            raise ValueError("Don't know how to parse object of type %s" % e.args[0])
        return parse(obj, name, root)

    def str_toxml(self, obj, name, root):
        string = SubElement(root, "String")
        name_ele = SubElement(string, "Name")
        name_ele.text = name
        val = SubElement(string, "Val")
        val.text = obj

        string.tail = name_ele.tail = val.tail = "\n"
        string.text = "\n"

    def iter_toxml(self, obj, name, root):
        obj = tuple(obj)
        self.list_toxml(obj, name, root)

    def int_toxml(self, obj, name, root):
        int_ = SubElement(root, 'U32')
        name_ele = SubElement(int_, "Name")
        name_ele.text = name
        val = SubElement(int_, "Val")
        val.text = str(obj)

        int_.tail = name_ele.tail = val.tail = "\n"
        int_.text = "\n"

    def list_toxml(self, obj, name, root):
        cluster = SubElement(root, "Cluster")
        name_ele = SubElement(cluster, "Name")
        name_ele.text = name
        numelts = SubElement(cluster, "NumElts")
        numelts.text = str(len(obj))

        cluster.tail = name_ele.tail = numelts.tail = "\n"
        cluster.text = "\n"

        for name, item in obj:
            self.dispatch(item, name, cluster)

    def dict_toxml(self, obj, name, root):
        cluster = SubElement(root, "Cluster")
        name_ele = SubElement(cluster, "Name")
        name_ele.text = name
        nelts = SubElement(cluster, "NumElts")
        nelts.text = str(len(obj))

        cluster.tail = name_ele.tail = nelts.tail = "\n"
        cluster.text = "\n"

        for k, v in obj.items():
            self.dispatch(v, k, cluster)

    def float_toxml(self, obj, name, root):
        float_ = SubElement(root, 'SGL')
        name_ele = SubElement(float_, "Name")
        name_ele.text = name
        val = SubElement(float_, "Val")
        val.text = str(obj)

        float_.tail = name_ele.tail = val.tail = "\n"
        float_.text = "\n"

    def obj_to_xml(self, obj, result="True"):
        """
        Main entrypoint. If object is a str, the tree puts the object
        as the sole contents of <Message>. Otherwise, the object is
        recursively parsed.
        """
        reply = Element("Reply")
        result_ele = SubElement(reply, "Result")
        result_ele.text = str(result)  # True -> "True", "True" -> "True"
        reply.text = ""
        if isinstance(obj, str):
            message = SubElement(reply, "Message")
            message.text = obj
            message.tail = ""

        else:
            # message is an object. the toplevel object doesn't get
            # the same <cluster>...</cluster> wrapper that nested
            # objects get, so we have to sloppily convert message
            # to its proper format.

            self.dispatch(obj, "Message", reply)
            msg_ele = reply[1]
            msg_ele.tag = "Message"
            msg_ele.tail = ""

            # msg_ele[0] is the <name>Message</name> element that
            # doesn't exist in the actual xml
            del msg_ele[0]

            # nelts = SubElement(message, "NumElts")
            # nelts.text = str(len(message))
            # nelts.tail = "\n"
            #
            # typ = type(message)
            # if typ == dict:




        return simple_xml_dump(reply)


xml_generator = HelloXMLGenerator()
obj_to_xml = xml_generator.obj_to_xml
