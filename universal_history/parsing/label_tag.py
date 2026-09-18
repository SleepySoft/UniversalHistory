"""
LabelTag format parser, ported from History/core.py.

Fixes vs legacy:
- legacy defect #2: ``label_tags_list_to_dict`` compared the label against
  the list instead of the dict (always True); duplicate labels now merge
  correctly.
"""

from __future__ import annotations

from .text_utils import suppress_print, list_unique
from .token_parser import (
    TokenParser,
    LABEL_TAG_TOKENS,
    LABEL_TAG_WRAPPERS,
    LABEL_TAG_ESCAPES_SYMBOLS,
)


class LabelTagParser:
    """
    Parse "LabelTag" format text. "LabelTag" format looks like this:

      label1: tag, tag1, tag2, tag3; label2: tag5, tag6, tag7
      label3: tag8, tag9    # Comments

    This text will be parsed to list in dict:
      {
          label1: [tag1, tag2, tag3],
          label2: [tag5, tag6, tag7],
          label3: [tag8, tag9],
      }
    """
    def __init__(self):
        self.__last_tags = []
        self.__label_tags = []

    def get_label_tags(self) -> list:
        return self.__label_tags

    @suppress_print
    def parse(self, text: str) -> bool:
        parser = TokenParser()
        parser.config(LABEL_TAG_TOKENS, LABEL_TAG_WRAPPERS, LABEL_TAG_ESCAPES_SYMBOLS)
        parser.reset()
        parser.attach(text)

        ret = True
        until = ''
        expect = []
        next_step = 'label'

        while not parser.reaches_end():
            token = parser.next_token()

            print('-> Read token: ' + token)

            if until != '':
                if token == until:
                    until = ''
                continue
            elif len(expect) > 0:
                if token not in expect:
                    ret = False
                    print('! Expect token: ' + str(expect) + ' but met: ' + token)
                expect = []

            if token == '#':
                until = '\n'
            elif token in [':', ',', '"""']:
                print('Drop token: ' + token)

            elif token == '\n' or token == ';':
                next_step = 'label'
            elif next_step == 'label':
                expect = [':', ';']
                next_step = 'tag'
                self.switch_label(token)
            elif next_step == 'tag':
                expect = [',', '\n', '"""', ';']
                self.append_tag(token)
            else:
                print('Should not reach here.')
        return ret

    def switch_label(self, label: str):
        self.__last_tags = []
        self.__label_tags.append((label, self.__last_tags))

    def append_tag(self, tag: str):
        if self.__last_tags is not None and tag not in self.__last_tags:
            self.__last_tags.append(tag)

    @staticmethod
    def label_tags_to_text(label: str, tags, new_line: str = '\n'):
        if label is None or len(label) == 0:
            return ''
        else:
            tag_text = LabelTagParser.tags_to_text(tags, True)
            if len(tag_text) == 0:
                return ''
        return label + ': ' + tag_text + new_line

    @staticmethod
    def tags_to_text(tags, persistence: bool = False):
        if tags is None:
            return ''
        if isinstance(tags, (list, tuple)):
            if persistence:
                tags = [LabelTagParser.check_wrap_tag(tag.strip()) for tag in tags]
            if len(tags) > 0:
                text = ', '.join(tags)
            else:
                return ''
        else:
            text = LabelTagParser.check_wrap_tag(tags)
        return text

    @staticmethod
    def check_wrap_tag(tag) -> str:
        if not isinstance(tag, str):
            tag = str(tag)
        tag = tag.replace('"""', '\\"""')
        # tag = tag.replace('\\', '\\\\')
        for token in LABEL_TAG_TOKENS:
            if token in tag:
                return '"""' + tag + '"""'
        return tag

    @staticmethod
    def label_tags_list_to_dict(label_tags_list: list) -> dict:
        label_tags_dict = {}
        for label, tags in label_tags_list:
            # Legacy defect #2 fix: was `if label not in label_tags_list`
            # (always True), which reset tags of duplicated labels.
            if label not in label_tags_dict:
                label_tags_dict[label] = []
            label_tags_dict[label].extend(tags)
        return label_tags_dict


class LabelTag:
    """
    Label tag structure wrapper.
    """
    def __init__(self):
        self.__label_tags = {}

    def reset(self):
        self.__label_tags.clear()

    def attach(self, label_tags_list: list):
        self.__label_tags = LabelTagParser.label_tags_list_to_dict(label_tags_list)

    def get_tags(self, label: str) -> list:
        return self.__label_tags.get(label, [])

    def get_labels(self) -> list:
        return list(self.__label_tags.keys())

    def get_label_tags(self) -> dict:
        return self.__label_tags

    def is_label_empty(self, label: str) -> bool:
        tags = self.__label_tags.get(label)
        tags_text = LabelTagParser.tags_to_text(tags)
        return tags_text == ''

    def add_tags(self, label: str, tags):
        if not isinstance(tags, (list, tuple)):
            tags = [tags]
        if label not in self.__label_tags.keys():
            self.__label_tags[label] = tags
        else:
            self.__label_tags[label].extend(tags)
        # list_unique is order-preserving in this port (legacy defect #6).
        self.__label_tags[label] = list_unique(self.__label_tags[label])

    def remove_label(self, label: str):
        if label in self.__label_tags.keys():
            del self.__label_tags[label]

    def dump_text(self, labels: list = None, compact: bool = False) -> str:
        text = ''
        new_line = '; ' if compact else '\n'
        if labels is None:
            labels = list(self.__label_tags.keys())

        for label in labels:
            tags = self.__label_tags.get(label)
            tags_text = LabelTagParser.tags_to_text(tags, True)
            if tags_text != '':
                text += label + ': ' + tags_text + new_line
        return text

    def filter(self,
               include_label_tags: dict, include_all: bool = True,
               exclude_label_tags: dict = None, exclude_any: bool = True) -> bool:
        if include_label_tags is not None and len(include_label_tags) > 0 and \
                not self.includes(include_label_tags, include_all):
            return False
        if exclude_label_tags is not None and len(exclude_label_tags) > 0 and \
                self.includes(exclude_label_tags, not exclude_any):
            return False
        return True

    def includes(self, label_tag_dict: dict, include_all: bool = False):
        result = False
        for key in label_tag_dict:
            if key not in self.__label_tags.keys():
                if include_all:
                    return False
                else:
                    continue
            expect_tags = label_tag_dict[key]
            exists_tags = self.__label_tags[key]
            for expect_tag in expect_tags:
                if expect_tag not in exists_tags:
                    if include_all:
                        return False
                else:
                    if include_all:
                        result = True
                    else:
                        return True
        return result
