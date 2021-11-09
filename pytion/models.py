# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Union, List, Any
from collections.abc import MutableSequence


# I wanna use pydantic, but API provide variable names of property


class RichText(object):
    def __init__(self, **kwargs) -> None:
        self.plain_text: str = kwargs.get("plain_text")
        self.href: Optional[str] = kwargs.get("href")
        self.annotations: Dict[str, Union[bool, str]] = kwargs.get("annotations")
        self.type: str = kwargs.get("type")
        self.data: Dict = kwargs[self.type]

    def __str__(self):
        return str(self.plain_text)

    def __repr__(self):
        return f"RichText({self.plain_text})"

    def __bool__(self):
        return bool(self.plain_text)

    # def __len__(self):
    #     return len(self.plain_text)

    def get(self) -> Dict[str, Any]:
        """
        Text type supported only
        """
        return {"type": "text", "text": {"content": self.plain_text, "link": None}}


class RichTextArray(MutableSequence):
    def __init__(self, array: List[Dict]) -> None:
        self.array = [RichText(**rt) for rt in array]

    def __getitem__(self, item):
        return self.array[item]

    def __setitem__(self, key, value):
        self.array[key] = value

    def __delitem__(self, key):
        del self.array[key]

    def __len__(self):
        return len(self.array)

    def insert(self, index: int, value) -> None:
        self.array.insert(index, value)

    def __str__(self):
        return " ".join(str(rt) for rt in self)

    def __repr__(self):
        return f"RichTextArray({str(self)})"

    def __bool__(self):
        return any(map(bool, self.array))

    def get(self) -> List[Dict[str, Any]]:
        return [item.get() for item in self]

    @classmethod
    def create(cls, text: str):
        return cls([{"type": "text", "plain_text": text, "text": {}}])


class Model(object):
    """
    :param id:
    :param object:
    :param created_time:
    :param last_edited_time:
    """

    def __init__(self, **kwargs) -> None:
        self.id = kwargs.get("id", "").replace("-", "")
        self.object = kwargs.get("object")
        self.created_time = self.format_iso_time(kwargs.get("created_time"))
        self.last_edited_time = self.format_iso_time(kwargs.get("last_edited_time"))
        self.raw = kwargs

    @classmethod
    def format_iso_time(cls, time: str) -> Optional[datetime]:
        if not time:
            return None
        return datetime.fromisoformat(time.replace("Z", "+00:00"))


class Property(object):
    def __init__(self, data: Dict[str, str]):
        self.to_delete = True if data.get("type") is None else False
        self.id: str = data.get("id")
        self.type: str = data.get("type") if data.get("type") else ""
        self.name: str = data.get("name")
        self.raw = data

    def __str__(self):
        return self.name if self.name else self.type

    def __repr__(self):
        return f"Property({self})"

    def get(self) -> Optional[Dict[str, Dict]]:
        # property removing while patch
        if self.to_delete:
            return None
        # property renaming while patch
        data = {}
        if self.name:
            data["name"] = self.name
        # property retyping while patch
        if self.type:
            data[self.type] = {}
        return data

    @classmethod
    def create(cls, type_: str = "", **kwargs):
        """
        Property Schema Object (watch docs)

        + addons:
        set type = `None` to delete this Property
        set param `name` to rename this Property
        """
        return cls({"type": type_, **kwargs})


class PropertyValue(Property):
    def __init__(self, data: Dict, name: str):
        super().__init__(data)
        self.name = name
        # self.raw_value = data.get(self.type)

        if self.type in ["title", "rich_text"]:
            if isinstance(data[self.type], list):
                self.value = RichTextArray(data[self.type])
            elif isinstance(data[self.type], RichTextArray):
                self.value = data[self.type]
            else:
                self.value = RichTextArray.create(data[self.type])

        if self.type == "number":
            self.value: Optional[int, float] = data["number"]

        if self.type == "select":
            if data["select"] and isinstance(data["select"], dict):
                self.value: Optional[str] = data["select"].get("name")
            elif data["select"] and isinstance(data["select"], str):
                self.value = data["select"]
            else:
                self.value = None

        if self.type == "multi_select":
            self.value: List[str] = [(v.get("name") if isinstance(v, dict) else v) for v in data["multi_select"]]

        if self.type == "checkbox":
            self.value: bool = data["checkbox"]

        if self.type == "date":
            if isinstance(data["date"], datetime):
                self.value = data["date"].isoformat()
                self.start = data["date"]
                self.end = None
            elif data["date"]:
                self.value: Optional[str] = data["date"].get("start")
                self.start: Optional[datetime] = Model.format_iso_time(data["date"].get("start"))
                self.end: Optional[datetime] = Model.format_iso_time(data["date"].get("end"))
            else:
                self.value = None
                self.start = None
                self.end = None

        if "time" in self.type:
            self.value: Optional[datetime] = Model.format_iso_time(data.get(self.type))

        if self.type == "formula":
            formula_type = data["formula"]["type"]
            if formula_type == "date":
                if data["formula"]["date"]:
                    self.value: str = data["formula"]["date"].get("start")
                    self.start: Optional[datetime] = Model.format_iso_time(data["formula"]["date"].get("start"))
                    self.end: Optional[datetime] = Model.format_iso_time(data["formula"]["date"].get("end"))
                else:
                    self.value = None
                    self.start = None
                    self.end = None
            else:
                self.value: Union[str, int, float, bool] = data["formula"][formula_type]

        if self.type == "created_by":
            self.value = "unsupported"

        if self.type == "last_edited_by":
            self.value = "unsupported"

        if self.type == "people":
            self.value = "unsupported"

        if self.type == "relation":
            self.value: List[str] = [item.get("id") for item in data["relation"]]

        if self.type == "rollup":
            rollup_type = data["rollup"]["type"]
            if rollup_type == "array":
                if len(data["rollup"]["array"]) == 0:
                    self.value = None
                elif len(data["rollup"]["array"]) == 1:
                    self.value = PropertyValue(data["rollup"]["array"][0], rollup_type)
                else:
                    self.value = [PropertyValue(element, rollup_type) for element in data["rollup"]["array"]]

            if rollup_type == "number":
                self.value: Optional[int, float] = data["rollup"]["number"]

            if rollup_type == "date":
                if data["rollup"]["date"]:
                    self.value: Optional[str] = data["rollup"]["date"].get("start")
                    self.start: Optional[datetime] = Model.format_iso_time(data["rollup"]["date"].get("start"))
                    self.end: Optional[datetime] = Model.format_iso_time(data["rollup"]["date"].get("end"))
                else:
                    self.value = None
                    self.start = None
                    self.end = None

        if self.type == "files":
            self.value = "unsupported"

        if self.type == "url":
            self.value: Optional[str] = data.get("url")

        if self.type == "email":
            self.value: Optional[str] = data.get("email")

        if self.type == "phone_number":
            self.value: Optional[str] = data.get("phone_number")

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"{self.name}({self})"

    def get(self):
        # checkbox can not be `None`
        if self.type in ["checkbox"]:
            return {self.type: self.value}

        # empty values
        if not self.value:
            if self.type in ["multi_select", "relation", "rich_text", "people", "files"]:
                return {self.type: []}
            return {self.type: None}

        # RichTextArray
        if self.type in ["title", "rich_text"] and hasattr(self.value, "get"):
            return {self.type: self.value.get()}

        # simple values
        if self.type in ["number", "url", "email", "phone_number"]:
            return {self.type: self.value}

        # select type
        if self.type == "select":
            return {self.type: {"name": self.value}}

        # multi-select type
        if self.type == "multi_select":
            return {self.type: [{"name": tag} for tag in self.value]}

        # date type
        if self.type == "date" and hasattr(self, "start") and hasattr(self, "end"):
            with_time = True if self.start.hour or self.start.minute else False
            if self.start:
                start = self.start.isoformat() if with_time else str(self.start.date())
            else:
                start = None
            if self.end:
                end = self.end.isoformat() if with_time else str(self.end.date())
            else:
                end = None
            return {self.type: {"start": start, "end": end}}

        # unsupported types:
        if self.type in ["files", "relation", "people"]:
            return {self.type: []}
        if self.type in ["created_time", "last_edited_by", "last_edited_time", "created_by"]:
            return None
        if self.type in ["formula", "rollup"]:
            return {self.type: {}}

    @classmethod
    def create(cls, type_: str = "", value: Any = None, **kwargs):
        """
        Property Value Object (watch docs)

        + addons:
        set type = `None` to delete this Property
        set param `name` to rename this Property
        """
        return cls({"type": type_, type_: value, **kwargs}, name="")


class Database(Model):
    object = "database"
    path = "databases"

    def __init__(self, **kwargs) -> None:
        """
        params from Model +
        :param cover:
        :param icon:
        :param title:
        :param properties:
        :param parent:
        :param url:
        """
        super().__init__(**kwargs)
        self.cover: Optional[Dict] = kwargs.get("cover")
        self.icon: Optional[Dict] = kwargs.get("icon")
        self.title = (kwargs.get("title")
                      if isinstance(kwargs["title"], RichTextArray) or not kwargs.get("title")
                      else RichTextArray(kwargs["title"])
                      )
        self.properties = {
            name: (value if isinstance(value, Property) else Property(value))
            for name, value in kwargs["properties"].items()
        }
        self.parent = kwargs["parent"] if isinstance(kwargs.get("parent"), LinkTo) else LinkTo(**kwargs["parent"])
        self.url: str = kwargs.get("url")

    def __str__(self):
        return str(self.title)

    def __repr__(self):
        return f"Database({self.title})"

    def get(self) -> Dict[str, Dict]:
        new_dict = {
            "parent": self.parent.get(),
            "properties": {name: value.get() for name, value in self.properties.items()}
        }
        if self.title:
            new_dict["title"] = self.title.get()
        return new_dict

    @classmethod
    def create(cls, parent: LinkTo, properties: Dict[str, Property], title: Optional[RichTextArray] = None, **kwargs):
        return cls(parent=parent, properties=properties, title=title, **kwargs)


class Page(Model):
    object = "page"
    path = "pages"

    def __init__(self, **kwargs) -> None:
        """
        params from Model +
        :param cover:
        :param icon:
        :param parent:
        :param archived:
        :param properties:
        :param url:
        """
        super().__init__(**kwargs)
        self.cover: Optional[Dict] = kwargs.get("cover")
        self.icon: Optional[Dict] = kwargs.get("icon")
        self.parent = kwargs["parent"] if isinstance(kwargs.get("parent"), LinkTo) else LinkTo(**kwargs["parent"])
        self.archived: bool = kwargs.get("archived")
        self.url: str = kwargs.get("url")
        self.properties = {
            name: (PropertyValue(data, name) if not isinstance(data, PropertyValue) else data)
            for name, data in kwargs["properties"].items()
        }
        for p in self.properties.values():
            if "title" in p.type:
                self.title = p.value
                break
        else:
            self.title = None

    def __str__(self):
        return str(self.title)

    def __repr__(self):
        return f"Page({self.title})"

    def get(self):
        return {
            "parent": self.parent.get(without_type=True),
            "icon": self.icon,  # optional
            "cover": self.cover,  # optional
            "properties": {name: p.get() for name, p in self.properties.items()},
            # todo children
        }

    @classmethod
    def create(
            cls, parent: LinkTo, properties: Dict[str, PropertyValue], title: Optional[RichTextArray] = None, **kwargs
    ):
        if title:
            if not properties:
                properties = {}
            properties["title"] = PropertyValue.create("title", title)
        return cls(parent=parent, properties=properties, **kwargs)


class Block(Model):
    object = "block"
    path = "blocks"

    def __init__(self, **kwargs):
        """
        params from Model +
        :param has_children:
        :param type:
        :param archived:
        """
        super().__init__(**kwargs)
        self.type: str = kwargs.get("type")
        self.has_children: bool = kwargs.get("has_children")
        self.archived: bool = kwargs.get("archived")
        self.children = LinkTo(block=self)
        self._level = kwargs["level"] if kwargs.get("level") else 0
        self.parent = None

        if self.type == "paragraph":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            # Paragraph Block does not contain `children` attr (watch Docs)

        if "heading" in self.type:
            self.text = RichTextArray(kwargs[self.type].get("text"))

        if self.type == "callout":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            self.icon: Dict = kwargs[self.type].get("icon")
            # Callout Block does not contain `children` attr (watch Docs)

        if self.type == "quote":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            # Quote Block does not contain `children` attr (watch Docs)

        if "list_item" in self.type:
            self.text = RichTextArray(kwargs[self.type].get("text"))
            # Block does not contain `children` attr (watch Docs)

        if self.type == "to_do":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            self.checked: bool = kwargs[self.type].get("checked")
            # To-do Block does not contain `children` attr (watch Docs)

        if self.type == "toggle":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            # Toggle Block does not contain `children` attr (watch Docs)

        if self.type == "code":
            self.text = RichTextArray(kwargs[self.type].get("text"))
            self.language: str = kwargs[self.type].get("language")

        if "child" in self.type:
            self.text = kwargs[self.type].get("title")
            if self.type == "child_page":
                self.parent = LinkTo(type="page", page=self.id)

        if self.type in ["embed", "image", "video", "file", "pdf", "breadcrumb"]:
            self.text = self.type

        if self.type == "bookmark":
            self.text: str = kwargs[self.type].get("url")
            self.caption = RichTextArray(kwargs[self.type].get("caption"))

        if self.type == "equation":
            self.text: str = kwargs[self.type].get("expression")

        if self.type == "divider":
            self.text = "---"

        if self.type == "table_of_contents":
            self.text = self.type

        if self.type == "unsupported":
            self.text = "*****"

    def __str__(self):
        return str(self.text)

    def __repr__(self):
        return f"Block({str(self.text)[:30]})"

    def get(self):
        if self.type in [
            "paragraph", "quote", "heading_1", "heading_2", "heading_3", "to_do",
            "bulleted_list_item", "numbered_list_item", "toggle", "callout", "code"
        ]:

            text = RichTextArray.create(self.text) if isinstance(self.text, str) else self.text
            new_dict = {self.type: {"text": text.get()}}
            if self.type == "to_do" and hasattr(self, "checked"):
                new_dict[self.type]["checked"] = self.checked
            if self.type == "code":
                new_dict[self.type]["language"] = getattr(self, "language", "plain text")
            return new_dict
        return None


class ElementArray(MutableSequence):
    class_map = {"page": Page, "database": Database, "block": Block}

    def __init__(self, array):
        self.array = []
        for ele in array:
            if ele.get("object") and ele["object"] in self.class_map:
                self.array.append(self.class_map[ele["object"]](**ele))

    def __getitem__(self, item):
        return self.array[item]

    def __setitem__(self, key, value):
        self.array[key] = value

    def __delitem__(self, key):
        del self.array[key]

    def __len__(self):
        return len(self.array)

    def insert(self, index: int, value) -> None:
        self.array.insert(index, value)

    def __str__(self):
        return "\n".join(str(b) for b in self)

    def __repr__(self):
        r = str(self)[:30].replace("\n", " ")
        return f"ElementArray({r})"


class BlockArray(ElementArray):
    def __str__(self):
        return "\n".join(b._level * "\t" + str(b) for b in self)

    def __repr__(self):
        r = str(self)[:30].replace("\n", " ")
        return f"BlockArray({r})"


class PageArray(ElementArray):
    def __repr__(self):
        r = str(self)[:30].replace("\n", " ")
        return f"PageArray({r})"


class LinkTo(object):
    """
    schema
    .type = `element_type`
    .id = `elementID`

    .get() - return API like style
    """

    def __init__(self, block: Optional[Block] = None, **kwargs):
        if block:
            self.type = block.object
            self.id = block.id
            self.after_path = "children"
            self.uri = "blocks"
        else:
            self.type: str = kwargs.get("type")
            self.id: str = kwargs.get(self.type) if kwargs.get(self.type) else kwargs.get("id")
            self.after_path = ""
            if self.type == "page_id":
                self.uri = "blocks"
            elif self.type == "database_id":
                self.uri = "databases"
            # when type is set manually
            elif self.type == "page":
                self.uri = "pages"
            else:
                self.uri = None

        if isinstance(self.id, str):
            self.id = self.id.replace("-", "")

    def get(self, without_type: bool = False):
        if without_type:
            return {self.type: self.id}
        return {"type": self.type, self.type: self.id}

    @classmethod
    def create(cls, **kwargs):
        """
        `.create(page_id="123412341234")`
        `.create(database_id="13412341234")`
        """
        for key, value in kwargs.items():
            return cls(type=key, id=value)
