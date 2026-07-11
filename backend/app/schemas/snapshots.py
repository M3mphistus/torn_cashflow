from .common import CamelModel


class SnapshotDTO(CamelModel):
    id: int
    synced_at: int
    money_onhand: int | None
    money_points: int | None
    vault_amount: int | None
    bank_amount: int | None
    energy_current: int | None
    energy_maximum: int | None
    nerve_current: int | None
    nerve_maximum: int | None
    happy_current: int | None
    happy_maximum: int | None
    networth: int | None
    nw_pending: int | None
    nw_wallet: int | None
    nw_bank: int | None
    nw_points: int | None
    nw_cayman: int | None
    nw_vault: int | None
    nw_piggybank: int | None
    nw_items: int | None
    nw_displaycase: int | None
    nw_bazaar: int | None
    nw_itemmarket: int | None
    nw_properties: int | None
    nw_stockmarket: int | None
    nw_auctionhouse: int | None
    nw_company: int | None
    nw_bookie: int | None
    nw_enlistedcars: int | None
    nw_loan: int | None
    nw_unpaidfees: int | None
    refills_total: int | None
    nerverefills_total: int | None
    energydrinkused_total: int | None
    xantaken_total: int | None
    war_mode_active: bool
    note: str | None


def snapshot_to_dto(row: dict) -> SnapshotDTO:
    return SnapshotDTO(**row)
