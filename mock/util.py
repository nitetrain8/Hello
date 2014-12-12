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


from io import BytesIO, StringIO


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
    b.write(tag.join(("<", ">")))

    txt = elem.text
    if txt:
        b.write(txt)

    for e in elem:
        _simple_xml_dump_inner_unicode(b, e)

    b.write(tag.join(("</", ">")))
    tail = elem.tail
    if tail:
        b.write(tail)


def simple_xml_dump(root, encoding="windows-1252"):
    """
    Simple XML tree generator for elements with nothing but
    a tag, text, tail, and children. No attributes supported.

    @param root: Root element for an xml document
    @return: bytes
    """
    b = StringIO()
    b.write('<?xml version="1.0" encoding="%s" standalone="no" ?>' % encoding)
    _simple_xml_dump_inner_unicode(b, root)
    return b.getvalue().encode(encoding)


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
            bytes: self.bytes_toxml,
            int: self.int_toxml,
            list: self.list_toxml,
            tuple: self.list_toxml,
            dict: self.dict_toxml,
            float: self.float_toxml,
            OrderedDict: self.dict_toxml,
            Element: self.ele_toxml,
            type(_ for _ in ""): self.iter_toxml  # generator
        }

    def register(self, typ, parsefunc):
        self.parse_types[typ] = parsefunc

    def parse(self, obj, name, root):
        try:
            parsefunc = self.parse_types[type(obj)]
        except KeyError as e:
            raise ValueError("Don't know how to parse object of type %s" % e.args[0])
        return parsefunc(obj, name, root)

    def ele_toxml(self, obj, name, root):
        root.append(obj)

    def bytes_toxml(self, obj, name, root):
        #: @type: str
        obj = obj.decode('utf-8')
        self.str_toxml(obj, name, root)

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

        try:
            for name, item in obj:
                self.parse(item, name, cluster)
        except:
            print(obj)
            raise

    def dict_toxml(self, obj, name, root):
        cluster = SubElement(root, "Cluster")
        name_ele = SubElement(cluster, "Name")
        name_ele.text = name
        nelts = SubElement(cluster, "NumElts")
        nelts.text = str(len(obj))

        cluster.tail = name_ele.tail = nelts.tail = "\n"
        cluster.text = "\n"

        for k, v in obj.items():
            self.parse(v, k, cluster)

    def float_toxml(self, obj, name, root):
        float_ = SubElement(root, 'SGL')
        name_ele = SubElement(float_, "Name")
        name_ele.text = name
        val = SubElement(float_, "Val")
        val.text = str(obj)

        float_.tail = name_ele.tail = val.tail = "\n"
        float_.text = "\n"

    def _create_hello_tree_msg(self, msg, reply):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8', 'strict')

        # check if object is iterable and not a string
        try:
            iter(msg)
        except TypeError:
            msg = str(msg)
        else:
            pass
        message = SubElement(reply, "Message")
        if isinstance(msg, str):
            message.text = msg
            message.tail = ""
        else:

            # after parsing the message, change the cluster tag to "message".
            self.parse(msg, "Message", message)
            message = reply[1]
            message.tag = "Message"
            message.text = ""
            message.tail = ""
            cluster = message[0]
            cluster.tail = ""

    def hello_tree_from_msg(self, msg, result="True"):
        """
        Main entrypoint. If object is a str, the tree puts the object
        as the sole contents of <Message>. Otherwise, the object is
        recursively parsed.
        """
        reply = Element("Reply")
        result_ele = SubElement(reply, "Result")
        result_ele.text = str(result)  # True -> "True", "True" -> "True"
        reply.text = ""

        self._create_hello_tree_msg(msg, reply)

        return reply

    def hello_xml_from_obj(self, obj, name):
        root = self.obj_to_xml(obj, name)
        return simple_xml_dump(root)

    def obj_to_xml(self, obj, name, root=None):
        if root is None:
            root = Element("Reply")
        self.parse(obj, name, root)
        return root

    def create_hello_xml(self, msg, result="True", encoding='windows-1252'):
        reply = self.hello_tree_from_msg(msg, result)
        return simple_xml_dump(reply, encoding)

    def tree_to_xml(self, tree, encoding):
        return simple_xml_dump(tree, encoding)


xml_generator = HelloXMLGenerator()
create_hello_xml = xml_generator.create_hello_xml
hello_tree_from_msg = xml_generator.hello_tree_from_msg
hello_xml_from_obj = xml_generator.hello_xml_from_obj


from json import JSONEncoder
from json.encoder import encode_basestring_ascii, encode_basestring, FLOAT_REPR, INFINITY, \
    _make_iterencode


class HelloJSONEncoder(JSONEncoder):
    """ This subclass existes entirely due to the fact that
    there is no built-in (public), accessible way to control
    the json representation of floats. So, this subclass
    fixes that.
    """
    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return "%.5f" % o

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text

        _iterencode = _make_iterencode(
            markers, self.default, _encoder, self.indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)
        return _iterencode(o, 0)


json_generator = HelloJSONEncoder(indent="\t")
dumps = json_generator.encode
