"""
HistoryRecord and HistoryRecordLoader, ported from History/core.py.

The ``History`` database class and ``HistoryRecordIndexer`` (legacy .index
pipeline) are intentionally NOT ported — UniversalHistory uses Workspace and
EventIndex instead.

Fixes vs legacy:
- #1: ``decimal_year_to_tick`` implemented in parsing.history_time, so
  since:/until: labels load instead of raising AttributeError.
- #3: people()/location()/organization() called a non-existent ``tags()``
  method; they now use ``get_tags()``.
- #4: ``duplicate_from`` shallow-copied the label dict (and read a
  mis-mangled attribute); it now deep-copies via ``get_label_tags()``.
- #5: unparseable time now stores int ``0`` instead of float ``0.0``.
- #7: ``from_file`` used to swallow all exceptions and return {} (failure
  indistinguishable from an empty file); it now raises ``OSError``.
- #9: directory loading now filters by the ``.his`` suffix by default.

The depot data still lives in the sibling legacy ``History/depot`` directory;
``get_local_depot_root()`` resolves that as a pure data path — there is no
code dependency on the History repository anymore.
"""

from __future__ import annotations

import os
import uuid
import ntpath
import posixpath
import traceback
from os import path

from . import history_time as HistoryTime
from .label_tag import LabelTag, LabelTagParser


# ----------------------------------------------- class HistoricalRecord -----------------------------------------------

class HistoryRecord(LabelTag):
    """
    History record will store in LabelTag format.

    Five key labels of a record: time, location, people, organization, event
    Optional common labels: title, brief, uuid, author, tags

    Every history record starts with [START] label. The "focus label" follows the [START] label. For example:

        [START]: event          # The start of a history record. This record focused on event (by default).
        [START]: people         # The start of a history record. This record focused on people.
    """

    def __init__(self, source: str = ''):
        super(HistoryRecord, self).__init__()
        self.__uuid = str(uuid.uuid4())
        self.__since = 0
        self.__until = 0
        self.__focus_label = ''
        self.__record_source = source

    # ------------------------------------------------------ Gets ------------------------------------------------------

    def uuid(self) -> str:
        return self.__uuid

    def since(self) -> HistoryTime.TICK:
        return self.__since

    def until(self) -> HistoryTime.TICK:
        return self.__until

    def source(self) -> str:
        return self.__record_source

    def get_focus_label(self) -> str:
        return self.__focus_label

    def copy_uuid_from(self, record):
        self.__uuid = record.__uuid

    def duplicate_from(self, record, includes_uuid: bool):
        # Legacy defect #4 fix: deep-copy the label dict instead of aliasing
        # it (the legacy line also read a mis-mangled attribute).
        super(HistoryRecord, self).reset()
        self.__since = record.__since
        self.__until = record.__until
        self.__focus_label = record.__focus_label
        self.__record_source = record.__record_source

        if includes_uuid:
            self.__uuid = record.__uuid
        for label, tags in record.get_label_tags().items():
            self.add_tags(label, list(tags))

    # -------------------------------------------

    def time(self) -> list:
        return self.get_tags('time')

    def people(self) -> list:
        # Legacy defect #3 fix: was self.tags('people') — no such method.
        return self.get_tags('people')

    def location(self) -> list:
        return self.get_tags('location')

    def organization(self) -> list:
        return self.get_tags('organization')

    def title(self) -> list:
        return self.get_tags('title')

    def brief(self) -> list:
        return self.get_tags('brief')

    def event(self) -> list:
        return self.get_tags('event')

    # ---------------------------------------------------- Features ----------------------------------------------------

    def reset(self):
        self.__focus_label = ''
        self.__record_source = ''
        super(HistoryRecord, self).reset()

    def set_source(self, source: str):
        self.__record_source = source

    def set_focus_label(self, label: str):
        self.__focus_label = label

    def set_label_tags(self, label: str, tags):
        if isinstance(tags, str):
            tags = [tags]
        tags = [tag.strip() for tag in tags]

        if label == 'uuid':
            self.__uuid = str(tags[0])
        elif label == 'time':
            self.__try_parse_time_tags(tags)
        elif label == 'since':
            self.__since = HistoryTime.decimal_year_to_tick(float(tags[0]))
            return
        elif label == 'until':
            self.__until = HistoryTime.decimal_year_to_tick(float(tags[0]))
            return
        elif label == 'source':
            self.__record_source = str(tags[0])
            return
        super(HistoryRecord, self).add_tags(label, tags)

    def to_index(self):
        record = HistoryRecord()
        record.index_for(self)
        return record

    def index_for(self, his_record):
        self.reset()
        self.__focus_label = 'index'
        self.__uuid = his_record.uuid()
        self.__since = his_record.since()
        self.__until = his_record.until()
        self.__record_source = his_record.source()

        abstract = LabelTagParser.tags_to_text(his_record.title())
        abstract = LabelTagParser.tags_to_text(his_record.brief()) if abstract == '' else abstract
        abstract = LabelTagParser.tags_to_text(his_record.event()) if abstract == '' else abstract
        self.set_label_tags('abstract', abstract.strip()[:50])

    def period_adapt(self, since: float, until: float):
        return (self.__since <= until) and (self.__until >= since)

    def dump_record(self, compact: bool = False) -> str:
        """
        Note that the focus label MUST be the last label of a History record.
        One History record should look like:
            [START]: focus_label
            other_label: content
            other_label: content
            .
            .
            .
            focus_label: content or 'end'
        """
        new_line = '; ' if compact else '\n'
        dump_list = self.__get_sorted_labels()

        # Default focus label is 'event'
        if self.__focus_label is None or self.__focus_label == '':
            self.__focus_label = 'event'

        # uuid should not in the common dump list
        if 'uuid' in dump_list:
            dump_list.remove('uuid')

        # Move the focus label to the tail.
        if self.__focus_label in dump_list:
            dump_list.remove(self.__focus_label)
        dump_list.append(self.__focus_label)

        # Extra: The start label of HistoricalRecord
        text = LabelTagParser.label_tags_to_text('[START]', self.__focus_label, new_line)

        # Extra: The uuid of event
        if self.__uuid is None or self.__uuid == '':
            self.__uuid = str(uuid.uuid4())
        text += LabelTagParser.label_tags_to_text('uuid', self.__uuid, new_line)

        # If it's an index. We should save the source.
        if self.__focus_label == 'index':
            text += LabelTagParser.label_tags_to_text('since', HistoryTime.tick_to_years(self.since())[0], new_line)
            text += LabelTagParser.label_tags_to_text('until', HistoryTime.tick_to_years(self.until())[0], new_line)
            text += LabelTagParser.label_tags_to_text('source', self.source(), new_line)

        # ---------------------- Dump common labels ----------------------

        text += super(HistoryRecord, self).dump_text(dump_list, compact)

        # If the focus label missing or its tag is empty, add it with 'end' tag
        if self.__focus_label not in dump_list or self.is_label_empty(self.__focus_label):
            text += LabelTagParser.label_tags_to_text(self.__focus_label, 'end', new_line)

        return text

    def __try_parse_time_tags(self, tags: list):
        his_times = HistoryTime.time_text_to_ticks(','.join(tags))
        if len(his_times) > 0:
            self.__since = min(his_times)
            self.__until = max(his_times)
        else:
            # Legacy defect #5 fix: was float 0.0; TICK is int.
            self.__since = 0
            self.__until = 0

    def __get_sorted_labels(self) -> list:
        priority_labels = {'time', 'people', 'location', 'organization'}
        tail_labels = {'title', 'brief', 'event'}
        existing_labels = set(self.get_labels())

        sorted_priority_labels = sorted(priority_labels & existing_labels)
        remaining_labels = sorted(existing_labels - priority_labels - tail_labels)
        sorted_tail_labels = sorted(tail_labels & existing_labels)

        sorted_labels = sorted_priority_labels + remaining_labels + sorted_tail_labels
        return sorted_labels

    # ----------------------------------------------------- print ------------------------------------------------------

    def __str__(self):
        return '---------------------------------------------------------------------------' + '\n' + \
                '|UUID   : ' + str(self.__uuid) + '\n' + \
                '|TIME   : ' + str(self.time()) + '\n' + \
                '|TITLE  : ' + str(self.title()) + '\n' + \
                '|BRIEF  : ' + str(self.brief()) + '\n' + \
                '|EVENT  : ' + str(self.event()) + '\n' + \
                '|SOURCE : ' + str(self.__record_source) + '\n' + \
                '---------------------------------------------------------------------------' \
               if self.__focus_label != 'index' else \
               '---------------------------------------------------------------------------' + '\n' + \
                '|UUID     : ' + str(self.uuid()) + '\n' + \
                '|SINCE    : ' + str(self.since()) + '\n' + \
                '|UNTIL    : ' + str(self.until()) + '\n' + \
                '|ABSTRACT : ' + str(self.get_tags('abstract')) + '\n' + \
                '|SOURCE   : ' + str(self.__record_source) + '\n' + \
                '---------------------------------------------------------------------------'


# --------------------------------------------------- class loader ----------------------------------------------------

class HistoryRecordLoader:

    ERROR_CODE_TYPE = str

    E_SUCCESS = 'Success'
    E_FAIL = 'Fail'
    E_SOURCE_NOT_EXISTS = 'Source not exists.'
    E_SOURCE_INVALID = 'Source invalid'
    E_SOURCE_READONLY = 'Source read-only'
    E_SOURCE_NOT_SUPPORT = 'Source not support'

    INVALID_SOURCE = '!@#$%&*?'         # These symbols can't be file name or url

    # ---------------------------------------- Save ----------------------------------------

    @staticmethod
    def to_source(source: str, records) -> ERROR_CODE_TYPE:
        if source == HistoryRecordLoader.INVALID_SOURCE:
            return HistoryRecordLoader.E_SOURCE_INVALID
        if HistoryRecordLoader.is_web_url(source):
            print('Web source: not support yet.')
            return HistoryRecordLoader.E_SOURCE_NOT_SUPPORT
        HistoryRecordLoader.to_local_source(source, records)
        return HistoryRecordLoader.E_SUCCESS

    @staticmethod
    def to_local_source(source: str, records) -> ERROR_CODE_TYPE:
        if not records:
            return HistoryRecordLoader.E_SOURCE_INVALID
        if not isinstance(records, (list, tuple)):
            records = [records]
        try:
            full_path = HistoryRecordLoader.source_to_absolute_path(source)
            print(f'| <= Write record: {full_path}')
            with open(full_path, 'wt', encoding='utf-8') as f:
                for record in records:
                    text = record.dump_record()
                    f.write(text)
            return HistoryRecordLoader.E_SUCCESS
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            return HistoryRecordLoader.E_FAIL

    # ---------------------------------------- Load ----------------------------------------

    @staticmethod
    def from_local_depot(depot: str) -> dict:
        depot_path = HistoryRecordLoader.join_local_depot_path(depot)
        return HistoryRecordLoader.from_directory(depot_path)

    @staticmethod
    def from_directory(directory: str) -> dict:
        # Legacy defect #9 fix: only .his files are parsed by default.
        files = HistoryRecordLoader.enumerate_local_path(directory, suffix=['.his'])
        return HistoryRecordLoader.from_files(files)

    @staticmethod
    def from_source(source: str) -> dict:
        if HistoryRecordLoader.is_web_url(source):
            return HistoryRecordLoader.from_web(source)
        else:
            return HistoryRecordLoader.from_file(HistoryRecordLoader.source_to_absolute_path(source))

    @staticmethod
    def from_files(files: list) -> dict:
        records = {}
        for file in files:
            r = HistoryRecordLoader.from_file(file)
            records.update(r)
        return records

    @staticmethod
    def from_web(url: str) -> dict:
        try:
            # Lazy import: requests is only needed for web sources.
            import requests
            r = requests.get(url)
            text = r.content.decode('utf-8')
            records = HistoryRecordLoader.from_text(text, url)
            return records
        except Exception as e:
            print('Error when fetching from web: ' + str(e))
            return {}

    @staticmethod
    def from_file(file: str) -> dict:
        """
        Load records from a single file.

        Legacy defect #7 fix: read failures raise OSError instead of being
        silently swallowed into {} — an empty file still loads successfully
        as {file: []}, so failure and emptiness are now distinguishable.
        """
        print('| => Load record: ' + file)
        with open(file, 'rt', encoding='utf-8') as f:
            records = HistoryRecordLoader.from_text(f.read(), file)
        return records

    @staticmethod
    def from_text(text: str, source: str = '') -> dict:
        error_list = []

        parser = LabelTagParser()
        parser.parse(text)

        focus = ''
        record = None
        records = []
        label_tags = parser.get_label_tags()

        for label, tags in label_tags:
            if label == '[START]':
                if record is not None:
                    records.append(record)
                record = None
                focus = ''
                if len(tags) == 0:
                    error_list.append('Missing start section.')
                else:
                    focus = tags[0]
                continue

            if record is None:
                record = HistoryRecord(HistoryRecordLoader.normalize_source(source))
                record.set_focus_label(focus)
            record.set_label_tags(label, tags)

            if focus != '' and label == focus and record is not None:
                records.append(record)
                record = None
                focus = ''
        if record is not None:
            records.append(record)
        return { source: records }

    # -------------------------------------- Assistance --------------------------------------

    @staticmethod
    def is_web_url(_path: str):
        return _path.startswith('http') or _path.startswith('ftp')

    @staticmethod
    def is_absolute_path(_path: str):
        return ntpath.isabs(_path) or posixpath.isabs(_path)

    @staticmethod
    def source_to_absolute_path(source: str) -> str:
        return source if \
            HistoryRecordLoader.is_absolute_path(source) else \
            path.join(HistoryRecordLoader.get_local_depot_root(), source)

    @staticmethod
    def normalize_source(source: str) -> str:
        depot_root = HistoryRecordLoader.get_local_depot_root()
        return source[len(depot_root) + 1:] if source.startswith(depot_root) else source

    @staticmethod
    def get_local_depot_root() -> str:
        # The depot is a data directory in the sibling legacy History
        # repository: <repo root>/History/depot. Pure path resolution —
        # no code is imported from History.
        # .../UniversalHistory/universal_history/parsing/history_record.py
        # -> parents: parsing / universal_history / UniversalHistory / <repo root>
        repo_root = path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
        depot_path = path.join(repo_root, 'History', 'depot')
        return path.normpath(depot_path)

    @staticmethod
    def join_local_depot_path(depot: str) -> str:
        root_path = HistoryRecordLoader.get_local_depot_root()
        depot_path = path.join(root_path, depot)
        return depot_path

    @staticmethod
    def enumerate_local_path(root_path: str, suffix: list = None) -> list:
        files = []
        for parent, dirnames, filenames in os.walk(root_path):
            for filename in filenames:
                if suffix is None:
                    files.append(path.join(parent, filename))
                else:
                    for sfx in suffix:
                        if filename.endswith(sfx):
                            files.append(path.join(parent, filename))
                            break
        return files
