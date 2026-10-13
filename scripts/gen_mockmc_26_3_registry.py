#!/usr/bin/env python3
"""
Extend MockMC's bundled registry fixtures so they cover every registry key that
Paper 26.3 requires and MockMC's 26.2 snapshot does not have.

Why this exists
---------------
MockMC is the only Bukkit server mock available, and its latest release
(mockmc-v26.2 0.0.5) ships registry data generated against Paper 26.2. When a
Paper 26.3 API class statically initialises -- MockMC eagerly initialises
ItemType, BlockType, GameEvent, DamageType, PotionType, MusicInstrument,
JukeboxSong, Art, Attribute, Biome and Sound, and tests touch others lazily --
it asks the registry for each key the 26.3 enum declares. MockMC's RegistryMock
answers getOrThrow(), so every absent key raises NoSuchElementException and
cascades into the whole test class erroring out.

MockMC loads registry data through getResourceAsStream("/keyed/<id>.json"), so a
same-path resource on the test classpath shadows the one inside the jar. This
script writes 26.3-complete copies of the affected files into
src/test/resources/keyed/.

How keys are obtained
---------------------
A constant's registry key is NOT always its lowercased name (for example
Sound.BLOCK_STRAW_BED_BREAK_LEAVE -> minecraft:block.straw_bed.break_leave).
So keys are read from the Paper class itself: the <clinit> of each of these
enums holds every key as a string literal immediately before the putstatic of
its constant. Lowercasing is only a fallback, and only for the two registries
whose keys are known to equal the constant name.

How entries are obtained
------------------------
Each missing entry is cloned from the most similar entry already in the same
26.2 fixture, then every self-reference inside it (key, name, translationKey,
typed, material, blockType, item_model, item_name, structureType, ...) is
retargeted to the new key. Field-specific invariants are preserved: ordinals
and map-decoration byte values stay unique, and a cloned item keeps or drops
blockType according to whether the new key is actually a block.

No test is disabled, skipped or weakened: the fixture only describes the same
registries the server under test will expose.

Run:  python3 scripts/gen_mockmc_26_3_registry.py
"""

import json
import os
import re
import subprocess
import sys
import zipfile
from copy import deepcopy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKMC_JAR_NAME = "mockmc-v26.2-0.0.5.jar"

# A key is a block if the material is shaped like one. Only used when the
# cloned template disagrees with the new key, e.g. so an item cloned from a
# wool slab does not gain a bogus blockType.
BLOCKISH = re.compile(
    r"(_log|_planks|_slab|_stairs|_fence|_fence_gate|_wall_sign|_hanging_sign|"
    r"_wall_hanging_sign|_door|_trapdoor|_pressure_plate|_button|_sign|_shelf|"
    r"_sapling|_leaves|_wood|_bed|_cushion|_shrub)$"
)
# Types that are rideable vehicles rather than living mobs.
VEHICLES = {"POPLAR_BOAT", "POPLAR_CHEST_BOAT", "BOAT", "CHEST_BOAT"}

# Stand-ins, tried in order, when no same-suffix sibling exists.
FALLBACK = {
    "item": ["minecraft:oak_sapling", "minecraft:paper", "minecraft:bowl"],
    "block": ["minecraft:oak_sapling", "minecraft:stone"],
    "entity_type": ["minecraft:armadillo", "minecraft:rabbit"],
    "worldgen/structure": ["minecraft:ancient_city"],
}

MOCK_JAR = None
PAPER = {}


# --------------------------------------------------------------------------- io

def find_mockmc_jar():
    for root, _dirs, files in os.walk(os.path.join(os.path.expanduser("~"), ".m2", "repository")):
        if MOCKMC_JAR_NAME in files:
            return os.path.join(root, MOCKMC_JAR_NAME)
    raise SystemExit(f"{MOCKMC_JAR_NAME} not found in ~/.m2")


def find_paper_jars():
    base = os.path.join(os.path.expanduser("~"), ".m2/repository/io/papermc/paper/paper-api")
    found = {}
    for d in sorted(os.listdir(base)):
        ver = ".".join(d.split(".")[:2])
        if ver not in ("26.2", "26.3"):
            continue
        for f in sorted(os.listdir(os.path.join(base, d))):
            if f.startswith("paper-api") and f.endswith(".jar") and "sources" not in f:
                found[ver] = os.path.join(base, d, f)
    for ver in ("26.2", "26.3"):
        if ver not in found:
            raise SystemExit(f"no paper-api {ver} jar under {base}")
    return found


def javap(jar, cls, code=False):
    args = (["javap", "-c"] if code else ["javap"]) + ["-p", "-cp", jar, cls]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"javap failed for {cls}")
    return r.stdout


def relation():
    with zipfile.ZipFile(MOCK_JAR) as z:
        names = set(z.namelist())
        rel = json.loads(z.read("registries/registry_key_class_relation.json"))
        fixtures = {
            i.split(":", 1)[1]: json.loads(z.read(f"keyed/{i.split(':', 1)[1]}.json"))
            for i in rel
            if f"keyed/{i.split(':', 1)[1]}.json" in names
        }
    return rel, fixtures


# ------------------------------------------------------------------ key lookup

def enum_constants(jar, cls):
    return set(re.findall(r"\b([A-Z][A-Z_0-9]{2,})\b", javap(jar, cls)))


def literal_keys(jar, cls):
    """constant name -> key literal, harvested from the enum's <clinit>."""
    out = javap(jar, cls, code=True)
    if "static {}" not in out:
        return {}
    pairs, pending = {}, None
    for line in out.split("static {}", 1)[1].splitlines():
        m = re.search(r"// String ([a-z][a-z0-9_./-]*)\s*$", line)
        if m:
            pending = m.group(1)
            continue
        m = re.search(r"putstatic\s+#\d+\s+// (?:Field|InterfaceMethodConstant) ([A-Z][A-Z_0-9]+)", line)
        if m and pending:
            pairs.setdefault(m.group(1), pending)
            pending = None
    return pairs


def needed_keys(cls):
    """constant name -> registry key, for every constant new in 26.3."""
    new = enum_constants(PAPER["26.3"], cls) - enum_constants(PAPER["26.2"], cls)
    literals = literal_keys(PAPER["26.3"], cls)
    out = {}
    for const in new:
        literal = literals.get(const)
        out[const] = f"minecraft:{literal}" if literal else f"minecraft:{const.lower()}"
    return out


# ------------------------------------------------------------- entry synthesis

def template_for(new_key, by_key, index, pool):
    suffix = new_key.rsplit("_", 1)[-1]
    for cand in index.get(suffix, []):
        if cand in by_key:
            return cand
    for cand in pool:
        if cand in by_key:
            return cand
    return None


def retarget(template_entry, new_key, new_const, registry_id):
    """Clone a fixture entry, rewriting every self-reference to the new key."""
    tkey = template_entry["key"]
    tname = tkey.split(":", 1)[1]
    nname = new_key.split(":", 1)[1]
    model = f"minecraft:{nname}"
    # Translation keys look like "item.minecraft.acacia_boat"; keep the
    # namespace the template used and only swap the path.
    tt = template_entry.get("translationKey", "")
    ns = tt[: tt.rindex("minecraft.")] if "minecraft." in tt else ""

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, str):
            if node == tkey or node == f"minecraft:{tname}":
                return new_key
            if ns and node == f"{ns}minecraft.{tname}":
                return f"{ns}minecraft.{nname}"
            return node
        return node

    out = walk(deepcopy(template_entry))
    out["key"] = new_key
    if "name" in out:
        out["name"] = new_const
    if "translationKey" in out:
        out["translationKey"] = f"{ns}minecraft.{nname}" if ns else out["translationKey"]

    if registry_id == "item":
        out["typed"] = model
        if "material" in out:
            out["material"] = model
        comps = out.get("createItemStack", {}).get("components", {})
        if "minecraft:item_model" in comps:
            comps["minecraft:item_model"] = model
        label = comps.get("minecraft:item_name")
        if isinstance(label, dict) and "translate" in label:
            label["translate"] = out.get("translationKey", f"item.minecraft.{nname}")
        # A key like minecraft:poplar_slab is a block; minecraft:paper is not.
        if BLOCKISH.search(nname):
            out["blockType"] = new_key
        else:
            out.pop("blockType", None)

    if registry_id == "entity_type" and "alive" in out:
        out["alive"] = new_const not in VEHICLES
    return out


def main():
    global MOCK_JAR, PAPER
    MOCK_JAR = find_mockmc_jar()
    PAPER = find_paper_jars()
    print(f"mockmc  : {MOCK_JAR}")
    print(f"paper   : {PAPER['26.3']}")

    rel, fixtures = relation()
    out_dir = os.path.join(REPO, "src", "test", "resources", "keyed")

    written, unresolved, grand_total = [], [], 0

    for full_id, cls in sorted(rel.items()):
        registry_id = full_id.split(":", 1)[1]
        if registry_id not in fixtures:
            continue
        doc = fixtures[registry_id]
        values = doc["values"]
        by_key = {e["key"]: e for e in values}
        index = {}
        for k in by_key:
            index.setdefault(k.rsplit("_", 1)[-1], []).append(k)
        for lst in index.values():
            lst.sort(key=lambda k: (len(k), k))

        want = needed_keys(cls)
        missing = [(c, k) for c, k in sorted(want.items()) if k not in by_key]
        if not missing:
            continue

        max_ordinal = max((e.get("ordinal", -1) for e in values), default=-1)
        max_value = max((e.get("value", -1) for e in values), default=-1)
        added, notes = [], []
        for const, key in missing:
            pool = FALLBACK.get(registry_id, [])
            if registry_id not in FALLBACK:
                # Small key-only registries (sounds, biomes, particles, map
                # decorations) can be cloned from any entry: they carry no
                # shape-dependent data.
                pool = [values[0]["key"]]
            template = template_for(key, by_key, index, pool)
            if template is None:
                unresolved.append(f"{registry_id}:{key}")
                continue
            entry = retarget(by_key[template], key, const, registry_id)
            if "ordinal" in entry or any("ordinal" in e for e in values):
                entry.pop("ordinal", None)
                max_ordinal += 1
                entry["ordinal"] = max_ordinal
            if "value" in entry:
                # Map decoration indexes must stay distinct.
                max_value += 1
                entry["value"] = max_value
            added.append(entry)
            if len(notes) < 3:
                notes.append(key)

        if not added:
            continue

        merged = values + added
        if any("ordinal" in e for e in merged):
            merged.sort(key=lambda e: e["ordinal"])
        else:
            merged.sort(key=lambda e: e["key"])
        path = os.path.join(out_dir, f"{registry_id}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"values": merged}, fh, indent="\t", sort_keys=True)
            fh.write("\n")
        grand_total += len(added)
        written.append((registry_id, len(values), len(merged), notes))

    for rid, before, after, notes in written:
        print(f"  {rid:24s} {before:5d} -> {after:5d}  (+{after - before})  e.g. {', '.join(notes)}")
    print(f"\n{grand_total} new registry entries written to src/test/resources/keyed/")

    if unresolved:
        print(f"UNRESOLVED ({len(unresolved)}): {' '.join(unresolved)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
