"""RAW rating sets RATE1..RATE12: the master's twelve ``OperationalLimitType``s, and each rated device's limits.

A device's nonzero ratings go in one ``OperationalLimitSet`` ``<eq>_ratings`` on its first terminal ``<eq>_T1``
(RAW-20). A zero rating is PSS/E's "no limit", so it writes no row. Ratings in MVA are ``ApparentPowerLimit``s;
ratings "in current expressed as MVA" (NXFRAT > 0) are ``CurrentLimit``s in kA (``ka_from_rating``; RAW-9).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#master`` (rating sets) and ``#branch`` (limits).
"""

from __future__ import annotations

from cimtables.document import Column, Row, Table

from cimhub_core.cimtbl import cell
from cimhub_raw.importer.cimtbl.derived import ka_from_rating

RATING_SETS = 12


def rating_type_mrid(set_number: int) -> str:
    return f"olt_rate{set_number}"


def rating_type_table(case) -> Table:
    """All twelve rating-set types, named from the RATING records; a set with no record is RATEn / RATING SET n."""
    records = {record.rating_set_number: record for record in case.ratings or []}
    rows = []
    for number in range(1, RATING_SETS + 1):
        record = records.get(number)
        name = record.rating_name if record and record.rating_name else f"RATE{number}"
        description = record.rating_description if record and record.rating_description else f"RATING SET {number}"
        rows.append(Row([rating_type_mrid(number), cell(name), cell(description)]))
    return Table("OperationalLimitType", [Column("mRID"), Column("name"), Column("description"),
                                          Column("direction", default="absoluteValue")], rows,
                 comment="rating sets RATE1..RATE12 (RAW-9)")


class RatingRows:
    """The limit-set and limit rows of a document's rated devices, collected device by device."""

    def __init__(self, in_current: bool):
        self.in_current = in_current
        self.sets: list[Row] = []
        self.limits: list[Row] = []

    def add(self, equipment_mrid: str, ratings, base_kv: float) -> None:
        """One set on ``<eq>_T1`` holding each nonzero RATEn; nothing when every rating is zero or blank."""
        numbered = [(number, rating) for number, rating in enumerate(ratings or [], start=1) if rating]
        if not numbered:
            return
        limit_set = f"{equipment_mrid}_ratings"
        self.sets.append(Row([limit_set, f"{equipment_mrid}_T1"]))
        for number, rating in numbered:
            value = ka_from_rating(rating, base_kv) if self.in_current else rating
            self.limits.append(Row([f"{equipment_mrid}_rate{number}", limit_set, rating_type_mrid(number),
                                    cell(value)]))

    def tables(self) -> list[Table]:
        if not self.sets:
            return []
        if self.in_current:
            limit_class, value_column, comment = "CurrentLimit", Column("normalValue", "kA"), \
                "NXFRAT > 0: derived, normalValue = RATEn / (sqrt(3) x BASKV) (ka_from_rating)"
        else:
            limit_class, value_column, comment = "ApparentPowerLimit", Column("normalValue", "MVA"), None
        return [
            Table("OperationalLimitSet", [Column("mRID"), Column("Terminal")], self.sets,
                  comment="ratings: one set on terminal 1 of each rated device; a zero RATEn is no limit (RAW-9, "
                          "RAW-20)"),
            Table(limit_class, [Column("mRID"), Column("OperationalLimitSet"), Column("OperationalLimitType"),
                                value_column], self.limits, comment=comment),
        ]
