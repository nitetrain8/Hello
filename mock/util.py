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
    txt = elem.text
    # short empty elements path
    if not len(elem) and not txt:
        b.write(''.join(("<", elem.tag, "/>", elem.tail or '')))
        return

    tag = elem.tag
    b.write(tag.join(("<", ">")))

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

    Also note that this class is relatively state-less: the only
    information stored within the instance is the registry of
    types to parse functions.

    It is intended that a single instance is reused over and over,
    for efficiency.

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
            bool: self.bool_toxml,
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

    def bool_toxml(self, obj, name, root):
        b = SubElement(root, 'Boolean')
        name_ele = SubElement(b, "Name")
        name_ele.text = name
        val = SubElement(b, "Val")

        # Currently, the only boolean passed by XML
        # by the webserver is the "Magnetic Wheel"
        # field of getVersion, which passes the bool
        # as a 0 or 1 (as opposed to True or False).

        val.text = str(int(obj))

        b.tail = name_ele.tail = val.tail = "\n"
        b.text = "\n"

    def list_toxml(self, obj, name, root):
        cluster = SubElement(root, "Cluster")
        name_ele = SubElement(cluster, "Name")
        name_ele.text = name
        numelts = SubElement(cluster, "NumElts")
        numelts.text = str(len(obj))

        cluster.tail = name_ele.tail = numelts.tail = "\n"
        cluster.text = "\n"

        for name, item in obj:
            self.parse(item, name, cluster)


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

    def _create_hello_tree_msg(self, msg, name, reply):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8', 'strict')

        message = SubElement(reply, "Message")
        # check if object is iterable and not a string
        try:
            iter(msg)
        except TypeError:
            msg = str(msg)

        if isinstance(msg, str):
            message.text = msg
            message.tail = ""
        else:

            # after parsing the message, change the cluster tag to "message".
            self.parse(msg, name, message)
            message = reply[1]
            message.tag = "Message"
            message.text = ""
            message.tail = ""
            cluster = message[0]
            cluster.tail = ""

    def hello_tree_from_msg(self, msg, name=None, result="True"):
        """
        Main entrypoint. If object is a str, the tree puts the object
        as the sole contents of <Message>. Otherwise, the object is
        recursively parsed.
        """
        reply = Element("Reply")
        result_ele = SubElement(reply, "Result")
        result_ele.text = str(result)  # True -> "True", "True" -> "True"
        reply.text = ""

        self._create_hello_tree_msg(msg, name, reply)

        return reply

    def hello_xml_from_obj(self, obj, name):
        root = self.obj_to_xml(obj, name)
        return simple_xml_dump(root)

    def obj_to_xml(self, obj, name, root=None):
        if root is None:
            root = Element("Reply")
        self.parse(obj, name, root)
        return root

    def create_hello_xml(self, msg, name=None, result="True", encoding='windows-1252'):
        reply = self.hello_tree_from_msg(msg, name, result)
        return simple_xml_dump(reply, encoding)

    def tree_to_xml(self, tree, encoding):
        return simple_xml_dump(tree, encoding)


xml_generator = HelloXMLGenerator()
create_hello_xml = xml_generator.create_hello_xml
hello_tree_from_msg = xml_generator.hello_tree_from_msg
hello_xml_from_obj = xml_generator.hello_xml_from_obj


from json import JSONEncoder
from json.encoder import encode_basestring_ascii, encode_basestring, INFINITY
FLOAT_REPR = float.__repr__


def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
                     _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
                     # # HACK: hand-optimized bytecode; turn globals into locals
                     ValueError=ValueError,
                     dict=dict,
                     float=float,
                     id=id,
                     int=int,
                     isinstance=isinstance,
                     list=list,
                     str=str,
                     tuple=tuple,
):


    if _indent is not None and not isinstance(_indent, str):
        _indent = ' ' * _indent

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, str):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + '1'
            elif value is False:
                yield buf + '0'
            elif isinstance(value, int):
                # Subclasses of int/float may override __str__, but we still
                # want to encode them as integers/floats in JSON. One example
                # within the standard library is IntEnum.
                yield buf + str(int(value))
            elif isinstance(value, float):
                # see comment above for int
                yield buf + _floatstr(float(value))
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = sorted(dct.items(), key=lambda kv: kv[0])
        else:
            items = dct.items()
        for key, value in items:
            if isinstance(key, str):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                # see comment for int/float in _make_iterencode
                key = _floatstr(float(key))
            elif key is True:
                key = '1'
            elif key is False:
                key = '0'
            elif key is None:
                key = 'null'
            elif isinstance(key, int):
                # see comment for int/float in _make_iterencode
                key = str(int(key))
            elif _skipkeys:
                continue
            else:
                raise TypeError("key " + repr(key) + " is not a string")
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, str):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield '1'
            elif value is False:
                yield '0'
            elif isinstance(value, int):
                # see comment for int/float in _make_iterencode
                yield str(int(value))
            elif isinstance(value, float):
                # see comment for int/float in _make_iterencode
                yield _floatstr(float(value))
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, str):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield '1'
        elif o is False:
            yield '0'
        elif isinstance(o, int):
            # see comment for int/float in _make_iterencode
            yield str(int(o))
        elif isinstance(o, float):
            # see comment for int/float in _make_iterencode
            yield _floatstr(float(o))
        elif isinstance(o, (list, tuple)):
            yield from _iterencode_list(o, _current_indent_level)
        elif isinstance(o, dict):
            yield from _iterencode_dict(o, _current_indent_level)
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            yield from _iterencode(o, _current_indent_level)
            if markers is not None:
                del markers[markerid]
    return _iterencode


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


json_generator = HelloJSONEncoder(indent="\t", ensure_ascii=False)
json_dumps = json_generator.encode
