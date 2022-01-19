#!/usr/local/env python3
import xml.etree.ElementTree as ET
import sys
import os
import argparse
import xmltodict
import math

absc = ["str", "dex", "con", "int", "wis", "cha"]

def as_list(x):
    # cause xml doesn't differentiate when there might be a single item or a
    # list of items at a given level
    if not isinstance(x, list):
        return([x])
    else:
        return x

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--infile",
        required=True,
        help="XML Fight Club file from Lion's Den Fight Club 5")
    parser.add_argument(
        "-c", "--compendium",
        required=True,
        help="Compendium for Lion's Den Fight Club 5")
    parser.add_argument(
        "--spells",
        help="Output all spells as well as character block" +
    "(useful to add to the end of your document)")

    # Parse and print the results
    return(parser.parse_args())


def parseXML(xmlfile):

    tree = ET.parse(xmlfile)
    root = tree.getroot()
    xmldict = XmlDictConfig(root)
    return(xmldict)

def get_ab_sc(x, score="dex"):
    x = x.split(",")
    for i, sc in enumerate(absc):
        if score == sc:
            return int(x[i])

def abmod(abscore):
    return(int(math.floor(abscore -10) * .5))

def pint(x):
    # pretty print an int
    if x >= 1:
        return (f"+{x}")
    else:
        return (f"{x}")

def extract_resistance(x):
    try:
        return(x.split("esistance against ")[1].split(" damage")[0])
    except IndexError:
        return([])

def extract_saves(x):
    try:
        return(x.split("saving throws against ")[1])
    except IndexError:
        return([])

def map_proficiency(x, absc):
    ski = '''Acrobatics
Animal Handling
Arcana
Athletics
Deception
History
Insight
Intimidation
Investigation
Medicine
Nature
Perception
Performance
Persuasion
Religion
Sleight of Hand
Stealth
Survival'''.split("\n")
    try:
        if (x >= 100):
            return(ski[x-100])
        else:
            return(absc[x])
    except:
        raise ValueError("Error parsing proficiency: %i" % x)



def pull_thing(d, name, value, match = "inlist"):
    # get things from lists of dicts. for instance,
    d = [x for x in d if name in x.keys()]
    if match == "strict":
        res_list = [x for x in d if x[name] == value]
    elif match == "in":
        res_list = [x for x in d if value in x[name]]
    elif match == "inlist":
        res_list = [x for x in d if x[name] in value]
    else:
        raise ValueError("Only match types are strict (exact matches), in, and inlist")
    return(res_list)


def get_class_levels(dat):
    levels = []
    for dat in as_list(dat):
        if "level" in dat.keys():
            levels.append(int(dat["level"]))
        else:
            levels.append(1)
    return(levels)

class PC:
    def __init__(self, cdat, comp):
        self.name = cdat["name"]
        self.cclass = [x["name"] for x in as_list(cdat["class"])]
        self.race = cdat["race"]["name"]
        self.absc = {x: 10 for x in absc}
        self.absc_w_mods = {x: 10 for x in absc}
        self.saves = {x: 0 for x in absc}
        self.get_absc_bases(cdat["abilities"])
        self.sp_block = ""
        self.slots = {}
        # Class
        self.level = get_class_levels(cdat["class"])
        self.profmod = math.ceil(sum(self.level) / 4)  + 1

        # Abilities/Attributes
        ress = []
        vulns = []
        profs = []
        armor = []
        for section in ["race", "class", "background"]:
            # these were list comprehensions but that is harder to debug
            for subsec in as_list(cdat[section]):
                for x in subsec["feat"]:
                    if "esistance" in x["text"]:
                        ress.append(extract_resistance(x["text"]))
            if "proficiency" in subsec.keys():
                for prof in as_list(subsec["proficiency"]):

                    profs.append(map_proficiency(int(prof), absc))
                #profs.extend([ for x in as_list(cdat[section]["proficiency"])])
        assert  [x for x in comp["race"] if x["name"].startswith(self.race)], "Race not found in compendium!"
        self.calc_absc(absc, race_abs = [x["ability"].split(",") for x in comp["race"] if x["name"].startswith(self.race)][0])
        self.calc_saves( profs)
        self.pp =  10 + abmod(self.absc_w_mods["wis"])
        self.calc_ac(cdat)
        self.get_spell_abmod(cdat)
        if self.sp_ab_mod:
            self.get_spells(cdat)
        self.get_speed(cdat)
        self.get_weapons_and_actions(cdat)
        self.skills = [x for x in profs if x  not in absc]
        if "feat" in cdat.keys():
            self.feat_list  = [x["name"] for x in as_list(cdat["feat"])]
        else:
            self.feat_list = []

    def get_absc_bases(self, abilities):
        for i,x in enumerate(abilities.strip().split(",")[0:6]):
            self.absc[absc[i]] = int(x)

    def calc_saves(self, profs):
        for x in absc:
            self.saves[x] = abmod(self.absc_w_mods[x])
            if x in profs:
                self.saves[x] = abmod(self.absc_w_mods[x]) + self.profmod

    def calc_absc(self, absc, race_abs):
        self.absc_w_mods = self.absc
        for x in race_abs:
            y, z = x.lower().strip().split(" ")
            self.absc_w_mods[y] = self.absc_w_mods[y] + int(z)

    def __repr__(self):
        return(str( self.__dict__))

    def calc_ac(self, cdat):
         # AC calculations:
         armor_list = ["Light Armor", "Medium Armor", "Heavy Armor", "Shield"]
         base_ac = 10
         try:
             armors = pull_thing(d=as_list(cdat["item"]), name="detail", value=armor_list, match="inlist")
             for armor in armors:
                 if armor["detail"] == "Shield":
                     base_ac += int(armor["ac"])
                 else:
                     base_ac = int(armor["ac"])
         except KeyError:
             print("No armor detected")
         self.AC =  abmod(self.absc["dex"]) + base_ac

    def get_spell_abmod(self, cdat):
        self.sp_ab_mod = []
        for c in as_list(cdat["class"]):
            try:
                self.sp_ab_mod.append([x["text"].split(" is your spellcasting ability")[0].split("\n")[-1].strip().lower()[0:3] for x in c["feat"] if x["name"] == "Spellcasting"][0])
            except IndexError:
                self.sp_ab_mod.append(None)

    def get_spells(self, cdat):
        self.spells = {}
        self.slots = [x["slots"].split(",") for x in as_list(cdat["class"])]
        self.spells = {"cantrips": []}
        dc_mod = [x for x in self.sp_ab_mod if x is not None][0]
        self.spell_save = 8 + self.profmod + abmod(self.absc_w_mods[dc_mod])
        self.spell_attack = self.spell_save - 8
        for c in as_list(cdat["class"]):

            if "spell" in c.keys(): # ["spell"]:
                for sp in c["spell"]:
                    try:
                        if sp["level"] in self.spells.keys():
                            self.spells[sp["level"]].append(sp["name"])
                        else:
                            self.spells[sp["level"]] = [sp["name"]]
                    except KeyError:
                        self.spells["cantrips"].append(sp["name"])
                self.sp_block = f'''>___\n>#### Spells
    > *({','.join([x if x is not None else "-" for x in self.sp_ab_mod])}), DC *{self.spell_save}*, attack {pint(self.spell_attack)}*'''
                for lev in ["cantrips", '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    if lev in self.spells.keys():
                        if self.spells[lev]: # ignore empty cantrip list
                            lev_lab = lev if lev == "cantrips" else f"{lev}  (*{','.join([x[int(lev)] for x in  self.slots])}*)"
                            self.sp_block += f"\n> - {lev_lab}: {', '.join(self.spells[lev])}"


    def get_weapons_and_actions(self, cdat):
        ## Attacks
        #attack_bonus  =
        self.at_block = f'''>#### Actions
> - ** Unarmed Strike ** {pint(abmod(self.absc_w_mods["str"] + self.profmod))} to hit, {1 + abmod(self.absc_w_mods["str"])} damage'''

        self.weapons = [x for x in as_list(cdat["item"]) if "weaponProperty" in  x.keys()]
        for wep in self.weapons :
            self.at_block += f'''\n> - ** {wep["name"]} ** {wep["damage1H"]} + (str/dex) damage'''

    def get_speed(self, cdat):
        # sometimes they dont specify :|
        try:
            self.speed = cdat["race"]["speed"]
        except KeyError:
            self.speed = 30

    def make_mod_or_save_string(self):
        res = ""
        for x in absc:
            res += pint(abmod(self.absc_w_mods[x]))
            if abmod(self.absc_w_mods[x]) != self.saves[x]:
                res += "(" + pint(self.saves[x]) + ")"
            res += "|"
        return(res)

def output_NPC_statblock(dat, comp):
    #print(dat)
    cdat = dat["pc"]["character"]
    cclass = comp["class"]
    thisPC = PC(cdat, comp)
    level_txt = ""
    text = f'''___
> ## {thisPC.name}
> *{"; ".join(["lv**" + str(thisPC.level[x]) + "** " +  thisPC.cclass[x]  for x in range(len(thisPC.cclass))])}* (prof {pint(thisPC.profmod)})
>___
> - ** Armor Class ** {thisPC.AC}
> - ** Hit Points ** {cdat["hpMax"]}
> - **Speed** {thisPC.speed} ft.
>___
>||STR|DEX|CON|INT|WIS|CHA|
>|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
>|Score|{"|".join([str(thisPC.absc_w_mods[x]) for x in absc])}|
>|Mod (ST)|{thisPC.make_mod_or_save_string()}|
>___
> - **Skills**:  {", ".join(thisPC.skills)}
> - **Senses**: passive Perception {thisPC.pp}
> - **Feats and Features**: {", ".join(thisPC.feat_list)}
> ___
{thisPC.at_block}
{thisPC.sp_block}
>___
'''
    return(text)

def make_spell_block(d):
    schools = {
        1: "Abjuration",
        2: "Conjuration",
        3: "Divination",
        4: "Enchantment",
        5: "Evocation",
        6: "Illusion",
        7: "Necromancy",
        8: "Transmutation"
    }

    comp = []
    for c in ["v", "s", "m"]:
        if c in d.keys() and d[c] == "1":
            comp.append(c)
    mat =  d["materials"] if "materials" in d.keys() else "none"
    lev =  d["level"] if "level" in d.keys() else "cantrip"
    tmp = f'''#### {d["name"]}
*Level: {lev} ({schools[int(d["school"])]})*
___
- **Casting Time:** {d["time"]}
- **Range:** {d["range"]}
- **Components:** {",".join(comp)} ({mat})
- **Duration:** {d["duration"]}

{d["text"]}
'''
    return((d["name"], "lev", tmp))

def output_spells(dat):
    cdat = dat["pc"]["character"]
    spells = []
    for section in ["race", "class", "background"]:
        for subsec in as_list(cdat[section]):
            if "spell" in subsec.keys():
                spells.extend([x for x in subsec["spell"] ])

    spell_dict = {}
    for d in spells:
        (name, lev, block) = make_spell_block(d)
        print(block)
        spell_dict[name] = (lev, block)
    return(spell_dict)

def main(args):
    sys.stderr.write("Parsing compendium\n")
    with open(args.compendium, "rb") as inf:
        comp = xmltodict.parse(inf)

    sys.stderr.write("parsing character sheet: %s\n" % args.infile)
    with open(args.infile, "rb") as inf:
        dat = xmltodict.parse(inf)
    sys.stderr.write("creating PC stat block")
    stat_block = output_NPC_statblock(dat, comp["compendium"])
    if args.spells:
        sys.stderr.write("outputting spell blocks")
        return(stat_block, output_spells(dat))
    else:
        return(stat_block, None)

if __name__ == "__main__":
    args = get_args()
    main(args)
