"""
Seed the IPC → BNS mapping table from the conversion guide (Table 3–8).
Run once: python -m scripts.seed_ipcbns_mapping
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import paths
from src.rag.vectorstore import IPCBNSRelationalStore

# IPC section → (BNS section, short note) from conversion tables in the PDF
MAPPINGS = [
    # Table 3: Offences Against Human Body
    ("299", "100", "Culpable homicide"),
    ("300", "101", "Murder"),
    ("302", "103", "Punishment for murder"),
    ("304", "105", "Culpable homicide not amounting to murder"),
    ("304A", "106", "Causing death by negligence"),
    ("304B", "80", "Dowry death"),
    ("306", "108", "Abetment of suicide"),
    ("307", "109", "Attempt to murder"),
    ("308", "110", "Attempt to culpable homicide"),
    ("320", "112", "Grievous hurt"),
    ("321", "113", "Voluntarily causing hurt"),
    ("323", "115", "Punishment for voluntarily causing hurt"),
    ("324", "117", "Voluntarily causing hurt by dangerous weapons"),
    ("325", "118", "Voluntarily causing grievous hurt"),
    ("326", "119", "Grievous hurt by dangerous weapons"),
    ("326A", "124", "Acid attack"),
    ("326B", "125", "Attempt to throw acid"),
    # Table 4: Sexual Offences
    ("354", "74", "Assault to outrage modesty"),
    ("354A", "75", "Sexual harassment"),
    ("354B", "76", "Assault to disrobe"),
    ("354C", "77", "Voyeurism"),
    ("354D", "78", "Stalking"),
    ("375", "63", "Rape"),
    ("376", "64", "Punishment for rape"),
    ("376A", "65", "Rape causing death"),
    ("376AB", "66", "Rape of woman under 12"),
    ("376B", "67", "Intercourse by husband during separation"),
    ("376C", "68", "Sexual intercourse by authority"),
    ("376D", "70", "Gang rape"),
    ("376DA", "70", "Gang rape on woman under 16"),
    ("376E", "71", "Repeat offenders rape"),
    # Table 5: Property
    ("378", "303", "Theft"),
    ("379", "303", "Punishment for theft"),
    ("380", "304", "Theft in dwelling house"),
    ("381", "305", "Theft by clerk or servant"),
    ("382", "309", "Theft after preparation for hurt"),
    ("383", "308", "Extortion"),
    ("384", "308", "Punishment for extortion"),
    ("392", "309", "Robbery"),
    ("395", "310", "Dacoity"),
    ("411", "316", "Receiving stolen property"),
    ("415", "318", "Cheating"),
    ("420", "318", "Cheating and inducing delivery"),
    # Table 6–8: Public tranquillity, state, public servants
    ("141", "189", "Unlawful assembly"),
    ("143", "191", "Member of unlawful assembly"),
    ("147", "191", "Rioting"),
    ("148", "192", "Rioting armed"),
    ("149", "191", "Offence by member of unlawful assembly"),
    ("153A", "196", "Promoting enmity between groups"),
    ("121", "147", "Waging war against Government"),
    ("124A", "152", "Sedition (replaced by BNS 152)"),
    ("166", "198", "Public servant disobeying law"),
    ("167", "199", "Framing incorrect document"),
    ("186", "132", "Obstructing public servant"),
    ("353", "121", "Assault to deter public servant"),
]


def main():
    store = IPCBNSRelationalStore(paths.SQLITE_DB)
    for ipc, bns, notes in MAPPINGS:
        store.upsert_mapping(ipc, bns, notes)
    print(f"[seed] Inserted {len(MAPPINGS)} IPC → BNS mappings into {paths.SQLITE_DB}")


if __name__ == "__main__":
    main()
