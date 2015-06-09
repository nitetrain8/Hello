"""

Created by: Nathan Starkweather
Created on: 04/09/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


def quotify(s):
    if not isinstance(s, str):
        s = str(s)
    if s.startswith("\"") and s.endswith("\""):
        return s
    return ''.join(("\"", s.strip("\"'"), "\""))


class _HTMLElement():
    tag = ""
    def __init__(self, tag, children=None, id=None, props=None):
        if props is None:
            props = {}
        if id is not None:
            props['id'] = quotify(id)
        self.tag = tag
        self.children = []
        if children:
            for c in children:
                self.add_child(c)
        self.props = props

    def add_property(self, key, value):
        self.props[key] = quotify(value)

    def write(self, f, indent=0):
        # tagline = "<" + self.tag + " ".join("%s=%s" % (key, quotify(value)) for key, value in self.props.items()) + ">"
        tagline = "".join(("<",
                           self.tag,
                           " " if self.props else "",
                           " ".join("%s=%s" % (key, quotify(value)) for key, value in self.props.items()),
                           ">"))
        f.write(indent * 4 * " ")
        f.write(tagline)
        if hasattr(self, "textcontent"):
            f.write(self.textcontent)
        if self.children:
            f.write("\n")
            for c in self.children:
                c.write(f, indent + 1)

            f.write(indent * 4 * " ")
        f.write(self.tag.join(("</", ">")))
        f.write('\n')

    def add_child(self, c):
        self.children.append(c)


class HTMLElement(_HTMLElement):
    def __init__(self, children=None, id=None, props=None):
        super().__init__(self.tag, children, id, props)


class TableCaption(HTMLElement):
    tag = "caption"
    def __init__(self, text):
        self.textcontent = text
        super().__init__()


class Table(HTMLElement):
    tag = "table"
    def __init__(self, children=None, id=None, caption=None):
        super().__init__(children, id)
        c = TableCaption(caption)
        self.add_child(c)


class TableRow(HTMLElement):
    tag = "tr"


class TableData(HTMLElement):
    tag = "td"
    def __init__(self, text, children=None, id=None):
        self.textcontent = text
        super().__init__(children, id)


class ControllerDummy():
    def __init__(self, prettyname, name):
        self.name = name
        self.prettyname = prettyname

    def ashtml(self, start=0):
        row = TableRow()

        namerow = TableData(self.prettyname)
        row.add_child(namerow)
        for i, derp in enumerate(("sp", "pv", "man", "manup", "mandown", "mode", "error", "interlock"), start):
            name = self.name + derp
            d = TableData('--', None, name)
            d.add_property("align", "center")
            row.add_child(d)
        return row

def main():
    sensors = "ag", "temp", "do", "ph", "condensor", "level", "pressure"
    names = "Agitation", "Temperature", "DO", "pH", "Condensor", "Level", "Pressure"

    table = Table(caption="HelloData")
    table.add_property("style", "width:50%")
    table.add_property("border", "3")
    table.add_property("cellspacing", "1")
    table.add_property("cellpadding", "5")

    i = 0
    for n, s in zip(names, sensors):
        table.add_child(ControllerDummy(n, s).ashtml(i))
        i += 9

    fp = "C:\\.replcache\\html.txt"
    with open(fp, 'w') as f:
        table.write(f)
    import os
    os.startfile(fp)

if __name__ == '__main__':
    main()

