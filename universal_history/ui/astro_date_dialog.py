"""
Astronomical date picker (BCE-capable): a custom year/month/day[/time] dialog
for dates outside the Qt calendar's 1-9999 range (decision phase 2 — the
hand-rolled BCE control).

Years use astronomical numbering directly: 0 = 1 BC, -1 = 2 BC. The UI shows
a BC/AD suffix next to the year spin so users do not need to know the mapping.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox,
    QVBoxLayout, QWidget,
)

from universal_history.chrono.jdn_timestamp import JDNTimestamp

# QSpinBox is int32; ±2 billion astronomical years is far beyond any
# hand-entered history while covering all of Deep Time's labeled range.
_MAX_YEAR = 2_000_000_000


class AstroDatePickerDialog(QDialog):
    """Year/Month/Day (+ optional time) picker for any astronomical year."""

    def __init__(self, initial: Optional[JDNTimestamp] = None,
                 with_time: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Pick Date & Time"))

        y, m, d, hh, mm, ss = (2000, 1, 1, 0, 0, 0)
        if initial is not None:
            y, m, d, hh, mm, ss, *_ = initial.to_gregorian()

        self._year = QSpinBox()
        self._year.setRange(-_MAX_YEAR, _MAX_YEAR)
        self._year.setValue(y)
        self._year.setGroupSeparatorShown(True)
        self._era = QLabel()
        self._year.valueChanged.connect(self._update_era)

        self._month = QSpinBox()
        self._month.setRange(1, 12)
        self._month.setValue(m)

        self._day = QSpinBox()
        self._day.setRange(1, 31)
        self._day.setValue(d)

        date_row = QHBoxLayout()
        date_row.addWidget(self._year)
        date_row.addWidget(self._era)
        date_row.addWidget(self._month)
        date_row.addWidget(self._day)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #b91c1c;")

        form = QFormLayout()
        form.addRow(self.tr("Year / Month / Day"), self._wrap(date_row))

        self._time_spins = None
        if with_time:
            self._hour = QSpinBox()
            self._hour.setRange(0, 23)
            self._hour.setValue(hh)
            self._minute = QSpinBox()
            self._minute.setRange(0, 59)
            self._minute.setValue(mm)
            self._second = QSpinBox()
            self._second.setRange(0, 59)
            self._second.setValue(ss)
            time_row = QHBoxLayout()
            time_row.addWidget(self._hour)
            time_row.addWidget(QLabel(":"))
            time_row.addWidget(self._minute)
            time_row.addWidget(QLabel(":"))
            time_row.addWidget(self._second)
            self._time_spins = (self._hour, self._minute, self._second)
            form.addRow(self.tr("Time"), self._wrap(time_row))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

        self._result: Optional[JDNTimestamp] = None
        self._update_era()

    @staticmethod
    def _wrap(row: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        return w

    def _update_era(self):
        y = self._year.value()
        self._era.setText("AD" if y > 0 else self.tr("BC (year %1)")
                          .replace("%1", str(1 - y)))

    def _on_accept(self):
        hh = mm = ss = 0
        if self._time_spins is not None:
            hh, mm, ss = (s.value() for s in self._time_spins)
        y, m, d = self._year.value(), self._month.value(), self._day.value()
        try:
            ts = JDNTimestamp.from_ymd_hms(y, m, d, hh, mm, ss)
        except (ValueError, OverflowError) as e:
            self._error.setText(self.tr("Invalid date: %1")
                                .replace("%1", str(e)))
            return
        # JDNTimestamp normalizes overflowing days (e.g. Feb 30 -> Mar 1);
        # reject such input instead of silently shifting the date.
        if ts.to_gregorian()[:3] != (y, m, d):
            self._error.setText(
                self.tr("Invalid date: %1").replace(
                    "%1", f"{y}-{m:02d}-{d:02d}")
            )
            return
        self._result = ts
        self.accept()

    def selected(self) -> Optional[JDNTimestamp]:
        """The chosen timestamp — valid only after Accepted."""
        return self._result
