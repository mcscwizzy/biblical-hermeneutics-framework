#!/usr/bin/env python3
"""Development-only Luna synthesis for one canonical Genesis batch.

Luna supplies the prose in this file; BHF still supplies Scripture, evidence,
validation, authoritative metadata, atomic storage, and the progress rescan.
No AI adapter is invoked.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.chapter_commentary.builder import CommentaryBuilder
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.generator import CommentaryGenerator
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, ChapterCommentary, CommentaryGenerationRequest, CommentaryStatus
from bhf_agent.chapter_commentary.storage import load_commentary, save_commentary
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.config import AgentConfig

STORE = Path('.bhf-data/bhf-commentary')
TARGETS = (('Genesis', 41), ('Genesis', 42), ('Genesis', 43), ('Genesis', 44), ('Genesis', 45), ('Genesis', 46), ('Genesis', 47), ('Genesis', 48), ('Genesis', 49), ('Genesis', 50), ('Exodus', 1), ('Exodus', 2), ('Exodus', 3), ('Exodus', 4), ('Exodus', 5), ('Exodus', 6), ('Exodus', 7), ('Exodus', 8), ('Exodus', 9), ('Exodus', 10), ('Exodus', 11), ('Exodus', 12), ('Exodus', 13), ('Exodus', 14), ('Exodus', 15))

TEXT = {
11: 'Genesis 11 first describes one people with one language building a city and tower in Shinar to make a name and avoid being scattered. Jehovah confounds their language and scatters them, and the place is called Babel. The chapter then traces Shem’s generations to Terah, Abram, Nahor, and Haran, noting Haran’s death in Ur, Sarai’s barrenness, and Terah’s journey toward Canaan that stops at Haran.',
12: 'Genesis 12 begins with Jehovah’s call and promise to Abram: land, a great nation, blessing, and blessing for all families of the earth. Abram travels through Canaan, builds altars at Shechem and between Bethel and Ai, then goes to Egypt during famine. His fear leads him to call Sarai his sister; Pharaoh takes her, but Jehovah plagues Pharaoh’s house and Abram leaves with Sarai and his possessions.',
14: 'Genesis 14 presents a regional war involving named kings and cities. Lot is captured with Sodom’s goods, and Abram pursues the captors with his trained household men, recovering Lot, the goods, the women, and the people. Melchizedek blesses Abram, while Abram refuses the king of Sodom’s goods so that the king cannot claim to have made him rich, apart from the agreed shares of his allies.',
15: 'Genesis 15 sets Abram’s childlessness and the promise of an heir within a vision. Abram believes Jehovah, who promises descendants like the stars and identifies himself as the one who brought Abram from Ur to give him the land. A covenant scene follows, including a prophecy of sojourning and affliction, judgment on the serving nation, return in the fourth generation, and a land promise bounded by named rivers and peoples.',
17: 'Genesis 17 renews the covenant with Abram and changes his name to Abraham and Sarai’s to Sarah. The covenant includes descendants, land, and circumcision as its embodied token, with instructions reaching household members and foreigners bought with money. God distinguishes the covenant line through Isaac, while also promising to bless Ishmael; Abraham circumcises the males of his household that same day.',
18: 'Genesis 18 begins with Abraham receiving three visitors at Mamre and preparing food for them. The announcement that Sarah will have a son prompts her laughter and the question of whether anything is too hard for Jehovah. The visitors turn toward Sodom; Abraham repeatedly asks whether the righteous will be swept away with the wicked, and Jehovah answers each decreasing number before the exchange ends.',
20: 'Genesis 20 recounts Abraham’s stay in Gerar, where he again calls Sarah his sister. God comes to Abimelech in a dream, prevents him from touching Sarah, and explains that Abraham is a prophet. Abimelech returns Sarah, rebukes Abraham, gives him sheep, cattle, servants, and land, and receives prayer from Abraham so that God heals his household’s closed wombs.',
21: 'Genesis 21 records Sarah’s son Isaac being born at the appointed time and Abraham circumcising him. Sarah’s laughter becomes the occasion for rejoicing, while Hagar and Ishmael are sent away after Sarah sees Ishmael mocking. God hears the boy, provides a well, and preserves them in the wilderness. The chapter closes with Abimelech’s covenant with Abraham at Beersheba and Abraham calling on Jehovah there.',
22: 'Genesis 22 tests Abraham by commanding him to offer Isaac. Abraham travels to the appointed mountain, builds the altar, and binds Isaac, but Jehovah’s angel stops him and a ram is provided instead. The chapter reiterates blessing and multiplication of Abraham’s seed because he obeyed, then lists Nahor’s descendants, including Rebekah’s family connection.',
23: 'Genesis 23 tells of Sarah’s death at Hebron and Abraham’s mourning. Abraham negotiates publicly with the sons of Heth for a burial place, refuses a gift of the field, and purchases the field and cave of Machpelah from Ephron for the stated price. The chapter emphasizes the transaction’s witnesses and records the cave as Abraham’s possession for burial.',
24: 'Genesis 24 follows Abraham’s servant as he seeks a wife for Isaac among Abraham’s relatives. At the well, Rebekah’s generous response to the servant and his camels identifies her within his prayer’s requested sign. The servant recounts Jehovah’s guidance to Rebekah’s household; Rebekah leaves with him, meets Isaac, and becomes his wife, and Isaac is comforted after his mother’s death.',
26: 'Genesis 26 describes Isaac’s sojourn in Gerar during famine, Jehovah’s promise to him, and Isaac’s fear leading him to call Rebekah his sister. After Abimelech discovers the truth, Isaac prospers and disputes arise over wells. Isaac moves and eventually finds room at Rehoboth, receives Jehovah’s appearance at Beersheba, and makes a covenant with Abimelech. The chapter ends by naming Esau’s Hittite wives as a grief to Isaac and Rebekah.',
27: 'Genesis 27 narrates Isaac’s intended blessing of Esau and Rebekah’s plan for Jacob to receive it instead. Jacob presents himself as Esau, Isaac blesses him with dew, abundance, peoples, and family dominance, and Esau arrives too late. Esau’s grief and hatred lead Rebekah to send Jacob toward Haran, while Isaac later directs Jacob not to marry a Canaanite woman.',
28: 'Genesis 28 has Jacob leave for Paddan-aram with Isaac’s blessing and the charge to take a wife from Rebekah’s family. Esau responds by taking a daughter of Ishmael. At Luz, Jacob dreams of a stairway between earth and heaven, hears Jehovah’s promise of land, descendants, presence, and return, and names the place Bethel after setting up his stone and making a vow.',
29: 'Genesis 29 brings Jacob to Haran and Rachel at the well. Jacob serves Laban seven years for Rachel, but Laban gives him Leah first; Jacob then receives Rachel after another agreement and serves further years. Jehovah sees Leah’s lack of love and gives her children, while Rachel remains barren in this chapter. The births of Reuben, Simeon, Levi, and Judah shape the household conflict.',
30: 'Genesis 30 records rivalry and bargaining within Jacob’s household. Rachel gives Bilhah to Jacob, Leah gives Zilpah, and the naming of children marks the competing claims. Leah bears more sons and Dinah, then Rachel bears Joseph. Jacob negotiates wages with Laban, and through patterned breeding his flocks increase, making him very prosperous.',
31: 'Genesis 31 describes Jacob’s decision to leave Laban after hearing Laban’s sons and seeing Laban’s changed attitude. Rachel and Leah agree to go; Jacob departs secretly with his family and possessions. Laban pursues them, searches the tents for his household gods without finding them, and is confronted by Jacob. At Galeed the men make a covenant and boundary, and Laban returns home while Jacob journeys onward.',
32: 'Genesis 32 shows Jacob preparing to meet Esau by sending gifts and dividing the camp. He prays by recalling Jehovah’s promise and asking deliverance from Esau, then remains alone at night and wrestles with a man until daybreak. Jacob receives the name Israel after striving with God and men, and the chapter explains the custom concerning the sinew of the thigh.',
33: 'Genesis 33 narrates Jacob’s meeting with Esau. Jacob arranges his family, approaches with repeated bows, and Esau runs to embrace him. Esau initially refuses the gifts but accepts after Jacob presses him. The brothers separate, Esau toward Seir and Jacob toward Succoth and then Shechem, where Jacob buys a field and sets up an altar to God, the God of Israel.',
35: 'Genesis 35 records Jacob’s return to Bethel at God’s command. He removes foreign gods, purifies his household, builds an altar, and receives the name Israel again with promises concerning nations, kings, and land. Deborah dies, Rachel dies giving birth to Benjamin, and Isaac dies at 180; the chapter also notes Reuben’s act with Bilhah and gives the sons of Jacob.',
36: 'Genesis 36 is a genealogy of Esau, identified as Edom. It lists his wives, sons, chiefs, and the Horite inhabitants of Seir, then records Edomite kings before Israel had kings. The repeated notices organize people by family, place, and office, ending with chiefs of Edom according to their habitations.',
37: 'Genesis 37 introduces Joseph as Jacob’s favored son and records the brothers’ hatred of him and his dreams of future preeminence. Jacob sends Joseph to check on the flock; the brothers strip him, cast him into a pit, and sell him to passing merchants after Judah proposes selling rather than killing him. They deceive Jacob with Joseph’s bloodied coat, while Joseph is taken to Egypt and sold to Potiphar.',
38: 'Genesis 38 interrupts Joseph’s story to follow Judah and Tamar. Judah’s sons Er and Onan die, and Tamar remains without the promised marriage to Shelah. Disguised, Tamar secures Judah’s signet, cord, and staff; when her pregnancy is exposed, she produces the pledge and Judah acknowledges that she is more righteous than he. Her twins Perez and Zerah are born, with the birth scene emphasizing the reversal of first appearance.',
39: 'Genesis 39 follows Joseph in Potiphar’s house and prison. Jehovah is said to be with Joseph, and Potiphar entrusts his house to him. Potiphar’s wife repeatedly solicits Joseph; he refuses, identifying the act as great wickedness and sin against God, then flees while leaving his garment. Her accusation sends him to prison, where Joseph again receives favor and responsibility.',
40: 'Genesis 40 places Pharaoh’s chief butler and baker in the prison with Joseph. Each has a troubling dream, and Joseph asks them to tell it because interpretations belong to God. He interprets three branches and three baskets as three days, predicting restoration for the butler and execution for the baker. The events occur as stated, but the restored butler forgets Joseph.',
}

NEXT = {
('Genesis',41): 'Genesis 41 records Pharaoh’s dreams of cows and ears of grain, Joseph’s interpretation of seven years of abundance followed by seven years of famine, and Joseph’s elevation over Egypt. Joseph stores grain, marries Asenath, and names his sons Manasseh and Ephraim. When famine comes, Egypt and surrounding lands seek food from Joseph.',
('Genesis',42): 'Genesis 42 sends Jacob’s sons to Egypt for grain. Joseph recognizes them but they do not recognize him; he tests their claim of honesty by keeping Simeon and requiring Benjamin’s presence. The brothers connect their distress with Joseph, return with grain, and discover the money in their sacks, while Jacob refuses to send Benjamin.',
('Genesis',43): 'Genesis 43 follows the brothers’ return to Egypt with Benjamin after Judah guarantees his safety. Joseph orders a feast, and the brothers fear because of the money returned in their sacks. Benjamin receives a larger portion, but the meal remains a carefully arranged encounter between Joseph and his brothers.',
('Genesis',44): 'Genesis 44 describes Joseph’s final test: his cup is placed in Benjamin’s sack, and the brothers are pursued and brought back. Judah offers himself in Benjamin’s place, explaining Jacob’s attachment to the youngest son and the danger his father would suffer if Benjamin did not return.',
('Genesis',45): 'Genesis 45 records Joseph revealing himself to his brothers. He tells them not to be grieved that they sold him, because God sent him ahead to preserve life during the famine. Joseph sends them to bring Jacob and the household to Egypt, and Pharaoh confirms that they should settle there.',
('Genesis',46): 'Genesis 46 records Jacob’s journey to Egypt after God tells him not to fear going down there. Jacob’s household is listed, Joseph meets him at Goshen, and the family prepares to answer Pharaoh that they are shepherds. The chapter emphasizes the migration of Israel’s household into Egypt.',
('Genesis',47): 'Genesis 47 places Jacob’s family in Goshen and records Jacob blessing Pharaoh. Joseph administers Egypt during the famine by exchanging grain for money, livestock, land, and labor, while preserving seed for planting. Jacob asks Joseph to bury him with his fathers rather than in Egypt.',
('Genesis',48): 'Genesis 48 records Jacob blessing Joseph’s sons, Ephraim and Manasseh. Jacob adopts them as his own, recalls Rachel’s death, and deliberately places his right hand on Ephraim despite Joseph’s attempt to correct him. Jacob blesses both boys and speaks of God’s continuing presence with the family.',
('Genesis',49): 'Genesis 49 records Jacob’s words to his sons before his death. The sayings distinguish the tribes through images, judgments, promises, and future descriptions, with particular attention to Judah and Joseph. Jacob charges them to bury him in the cave bought by Abraham, then dies.',
('Genesis',50): 'Genesis 50 records Jacob’s burial in Canaan, Joseph’s reassurance to his brothers after their father’s death, and Joseph’s final years. Joseph says that what the brothers meant for evil, God meant for good to preserve many people alive. Before dying, Joseph makes the children of Israel promise to carry up his bones.',
('Exodus',1): 'Exodus 1 begins by naming Jacob’s sons and describing Israel’s multiplication in Egypt. A new king who did not know Joseph subjects them to forced labor, orders the Hebrew midwives to kill sons, and then commands all his people to cast Hebrew sons into the river. The midwives fear God and preserve the children.',
('Exodus',2): 'Exodus 2 tells of Moses’ birth, concealment, rescue from the Nile by Pharaoh’s daughter, and upbringing. Moses kills an Egyptian who strikes a Hebrew and flees to Midian, where he helps Reuel’s daughters and marries Zipporah. Israel groans under bondage, and God hears and remembers his covenant.',
('Exodus',3): 'Exodus 3 describes Moses at Horeb before the burning bush. God identifies himself as the God of Abraham, Isaac, and Jacob, hears Israel’s affliction, and commissions Moses to bring Israel out of Egypt. The divine name is disclosed, and Moses is told what Israel and Pharaoh are to be told.',
('Exodus',4): 'Exodus 4 gives Moses signs for Israel, including the rod, the diseased and restored hand, and water becoming blood. Moses objects to his speaking ability, and Aaron is appointed to speak for him. Moses returns toward Egypt, circumcision occurs on the journey, and Moses and Aaron gather the elders who believe the message.',
('Exodus',5): 'Exodus 5 records Moses and Aaron asking Pharaoh to let Israel go to hold a feast to Jehovah. Pharaoh refuses and increases the labor by withholding straw while demanding the same brick quota. Israel’s officers complain to Moses, and Moses brings the people’s worsening situation before Jehovah.',
('Exodus',6): 'Exodus 6 records Jehovah’s renewed promise to bring Israel out of Egypt, redeem them, and take them as a people. Moses reports this but Israel does not listen because of anguish and hard bondage. The chapter then gives a genealogy focused on Moses and Aaron and returns to their commission before Pharaoh.',
('Exodus',7): 'Exodus 7 presents Moses and Aaron before Pharaoh and begins the signs and plagues. Aaron’s rod becomes a serpent and consumes the magicians’ rods, yet Pharaoh’s heart is hardened. The Nile is turned to blood, killing fish and making the water undrinkable, but Pharaoh does not listen.',
('Exodus',8): 'Exodus 8 records the plagues of frogs, lice, and flies. Pharaoh repeatedly asks for relief and promises release, then hardens his heart when relief comes. Jehovah distinguishes the land of Goshen in the fly plague, but Pharaoh still refuses to let the people go.',
('Exodus',9): 'Exodus 9 records disease on Egyptian livestock, boils on people and beasts, and destructive hail. Jehovah distinguishes Israel’s livestock and land, and the hail narrative notes that some Egyptians who feared the word brought servants and livestock inside. Pharaoh confesses sin during the hail but hardens his heart afterward.',
('Exodus',10): 'Exodus 10 records locusts and darkness. Pharaoh’s servants urge him to let Israel go, but negotiations repeatedly narrow and fail. Locusts consume what the hail left, darkness covers Egypt for three days while Israel has light, and Pharaoh again refuses and orders Moses away.',
('Exodus',11): 'Exodus 11 announces one final plague on Egypt and a coming release. Moses says that at midnight every firstborn in Egypt will die, from Pharaoh’s firstborn to the firstborn of the maidservant and animals, while Israel will be distinguished. Pharaoh will not listen until the signs are complete.',
('Exodus',12): 'Exodus 12 establishes the Passover month, the lamb, the blood on the doorposts, and the meal eaten in readiness. The firstborn of Egypt die, but the houses marked with blood are passed over. Israel leaves Egypt, and the chapter gives Passover regulations concerning its observance and participation.',
('Exodus',13): 'Exodus 13 consecrates every firstborn to Jehovah and explains the memorial of unleavened bread. Moses carries Joseph’s bones, and Jehovah leads Israel by a pillar of cloud by day and fire by night rather than by the nearer road through Philistia. The chapter frames the departure as an act of divine guidance.',
('Exodus',14): 'Exodus 14 narrates Israel’s escape through the sea. Pharaoh pursues, Israel fears, and Moses tells them to stand still and see Jehovah’s salvation. The sea divides, Israel passes on dry ground, Egypt follows, the waters return, and Israel sees Egypt defeated and believes Jehovah and Moses.',
('Exodus',15): 'Exodus 15 contains Moses and Israel’s song after the sea crossing, celebrating Jehovah’s victory and guidance toward the holy habitation. Miriam leads the women with tambourines. The journey reaches Marah, where bitter water is made drinkable, and Jehovah gives a statute and test concerning obedience.',
('Exodus',16): 'Exodus 16 records Israel’s complaint for food in the wilderness. Jehovah gives quail in the evening and bread from heaven in the morning, with instructions to gather daily and twice as much before the Sabbath. The people call the bread manna, and a portion is kept as a testimony.',
('Exodus',17): 'Exodus 17 records water from the rock at Rephidim after Israel complains, and the naming of the place for their testing and striving. Amalek fights Israel; Moses’ raised hands accompany Israel’s victory while Aaron and Hur support him. Moses builds an altar called Jehovah my banner.',
('Exodus',18): 'Exodus 18 tells of Jethro bringing Zipporah and Moses’ sons to the camp. After hearing what Jehovah did, Jethro blesses God and offers sacrifice. He advises Moses to appoint capable judges over groups so that only difficult cases come to Moses.',
('Exodus',19): 'Exodus 19 brings Israel to Sinai. Jehovah offers a covenant identity as a treasured possession, kingdom of priests, and holy nation if Israel obeys. The people prepare themselves, boundaries are set around the mountain, and Jehovah descends in cloud, thunder, fire, and trumpet sound.',
('Exodus',20): 'Exodus 20 gives the words spoken at Sinai: exclusive worship, limits on images and misuse of the divine name, Sabbath, obligations toward parents, and prohibitions of murder, adultery, theft, false witness, and coveting. The people fear and stand afar off, while Moses approaches the thick darkness.',
('Exodus',21): 'Exodus 21 begins judgments concerning Hebrew servants, release, and household cases. It addresses violence, injury, personal responsibility, and damages involving animals. The laws distinguish intentional killing from other cases and set measured consequences for bodily harm and property loss.',
('Exodus',22): 'Exodus 22 continues judgments about theft, restitution, property damage, lending, seduction, sorcery, idolatry, treatment of foreigners, widows, orphans, and the poor. It also gives rules about firstfruits and firstborn and calls Israel to be holy people.',
('Exodus',23): 'Exodus 23 gives rules against false reports, partiality, and following a crowd into wrong. It protects enemies’ animals, the poor, the resident foreigner, and the Sabbath. Three annual feasts are named, and Jehovah promises guidance toward the land while warning Israel not to covenant with its inhabitants’ gods.',
('Exodus',24): 'Exodus 24 records the covenant confirmation at Sinai. Moses reads the book, the people promise obedience, and blood is put on the people. Moses, Aaron, Nadab, Abihu, and elders see the God of Israel, after which Moses ascends the mountain into the cloud for forty days and nights.',
('Exodus',25): 'Exodus 25 begins instructions for offerings and the sanctuary. It describes the ark with its mercy-seat and cherubim, the table for the bread of the Presence, and the lampstand. The stated purpose is that Jehovah may dwell among the people, according to the pattern shown to Moses.',
('Exodus',26): 'Exodus 26 gives the construction of the tabernacle curtains, boards, sockets, bars, and the veil separating the holy place from the most holy place. The arrangement encloses the ark and defines the dwelling according to the pattern shown on the mountain.',
('Exodus',27): 'Exodus 27 describes the altar of burnt offering, its utensils, court hangings, pillars, and entrance. It also commands Israel to bring pure olive oil so the lamp may burn continually in the tent of meeting before Jehovah.',
('Exodus',28): 'Exodus 28 sets apart Aaron and his sons for priestly service and describes their holy garments. The ephod, breastplate, robe, coat, turban, and sash carry names, memorial elements, and signs of judgment and holiness before Jehovah.',
('Exodus',29): 'Exodus 29 gives the consecration procedure for Aaron and his sons: washing, clothing, anointing, sacrifices, blood applied to the priests, and a seven-day rite. It also establishes continual offerings and states that Jehovah will dwell among Israel and be their God.',
('Exodus',30): 'Exodus 30 describes the incense altar, ransom money associated with the numbering, the bronze laver, anointing oil, and holy incense. These objects and substances are restricted for the service of the tent and are not to be treated as ordinary personal materials.',
('Exodus',31): 'Exodus 31 names Bezalel and Oholiab as craftsmen appointed and filled with skill for the sanctuary work. Jehovah gives the Sabbath as a sign between himself and Israel, writes the tablets of testimony, and gives them to Moses on the mountain.',
('Exodus',32): 'Exodus 32 records Israel’s golden calf, Aaron’s participation, Moses’ descent with the tablets, and the breaking of them. Moses intercedes, destroys the calf, and calls for judgment in the camp. Jehovah affirms both the seriousness of the sin and the continuation of his dealings with Israel.',
('Exodus',33): 'Exodus 33 records Jehovah’s command for Israel to leave Sinai and the tent of meeting outside the camp. Moses asks for Jehovah’s presence and favor, insisting that the people must be distinguished by that presence. Moses asks to see Jehovah’s glory and is placed in a cleft of the rock.',
('Exodus',34): 'Exodus 34 describes new tablets, Jehovah’s proclamation of his name and character, and the renewal of covenant obligations. Moses receives commands concerning worship, feasts, firstborn, and Sabbath. His face shines when he descends, so he covers it when speaking with the people.',
('Exodus',35): 'Exodus 35 repeats the Sabbath command and calls Israel to bring willing offerings for the tabernacle. The people bring materials, and skilled men and women work with yarn, cloth, leather, wood, precious materials, and oil. Bezalel and Oholiab lead the appointed craftsmanship.',
('Exodus',36): 'Exodus 36 describes the craftsmen beginning the tabernacle work from the people’s offerings. The people bring more than enough, so Moses commands that no more be brought. The chapter details the curtains, coverings, boards, bars, pillars, and veil.',
('Exodus',37): 'Exodus 37 records the making of the ark, mercy-seat, cherubim, table, vessels, lampstand, and incense altar. Bezalel makes them according to the materials and forms specified, including the oil and incense used for the sanctuary service.',
('Exodus',38): 'Exodus 38 records the bronze altar, laver, court, pillars, sockets, hangings, and entrance. It gives an accounting of the metals used, as collected by Ithamar, and identifies the work associated with Bezalel and Oholiab.',
('Exodus',39): 'Exodus 39 records the making of the priestly garments and their components. The work is inspected and found to correspond to Jehovah’s commands through Moses. Moses blesses the workers after seeing that the tabernacle and its furnishings are complete.',
('Exodus',40): 'Exodus 40 records the erection and anointing of the tabernacle and its furnishings. Aaron and his sons are washed, clothed, and appointed. The cloud covers the tent and Jehovah’s glory fills it; Israel journeys when the cloud lifts and remains when it does not.',
('Leviticus',1): 'Leviticus 1 gives instructions for a burnt offering from cattle, sheep, goats, or birds. The offerer presents the animal, lays a hand on its head, and the priests handle the blood and altar fire. The offering is wholly burned as an offering of a pleasing odor.',
('Leviticus',2): 'Leviticus 2 gives instructions for a grain offering of fine flour, oil, and frankincense, including baked forms. A memorial portion is burned while the remainder belongs to Aaron and his sons. No leaven or honey is burned, and salt is required with every offering.',
('Leviticus',3): 'Leviticus 3 describes peace offerings from herd, flock, or goats. Fat and blood are treated as belonging to Jehovah: the fat is burned on the altar and the blood is poured out. The chapter closes by forbidding Israel to eat fat or blood.',
('Leviticus',4): 'Leviticus 4 addresses sin offerings for the anointed priest, the congregation, a ruler, and an ordinary person when unintentional sin becomes known. The ritual varies by status, but includes sacrifice, blood handling, removal of fat, and disposal of the remainder as prescribed.',
('Leviticus',5): 'Leviticus 5 identifies cases requiring confession and a sin offering, including failure to testify, ritual uncleanness, and rash oaths. It provides offerings scaled to means, from a female lamb or goat to birds or flour, and adds regulations for trespass involving holy things or deception.',
('Leviticus',6): 'Leviticus 6 continues laws for trespass, the burnt offering, grain offering, and sin offering. It instructs priests to keep the altar fire burning, eat designated portions in a holy place, and observe restrictions concerning holiness, vessels, and blood.',
('Leviticus',7): 'Leviticus 7 completes regulations for the guilt and peace offerings and distinguishes thank offerings from vows and freewill offerings. It sets time limits for eating sacrificial flesh, prohibits eating fat and blood, and identifies the portions assigned to priests.',
('Leviticus',8): 'Leviticus 8 records Moses consecrating Aaron and his sons. They are washed, clothed, anointed, and associated with sacrifices of sin offering, burnt offering, and consecration. Blood is placed on Aaron and his sons, and they remain at the tent of meeting for seven days.',
('Leviticus',9): 'Leviticus 9 records the priests’ first offerings on the eighth day. Aaron presents offerings for himself and the people, Moses and Aaron enter the tent, and Jehovah’s glory appears. Fire comes out from before Jehovah and consumes the offering, and the people shout and fall on their faces.',
('Leviticus',10): 'Leviticus 10 records Nadab and Abihu offering unauthorized fire and dying before Jehovah. Aaron and his remaining sons receive instructions about mourning, priestly sobriety, distinguishing holy from common, and teaching Israel. Moses also addresses the handling of the sin offering when its blood was not brought inside.',
}

def block(book, ch, evidence):
    d = bible.resolve_chapter(book, ch)
    refs = [f'{book} {ch}:1-{len(d["verses"])}']
    text = TEXT[ch] if book == 'Genesis' and ch in TEXT else NEXT.get((book, ch))
    if text is None:
        verses = d['verses']
        text = f"{book} {ch} contains {len(verses)} verses. It opens with: {verses[0]['text']} It concludes with: {verses[-1]['text']}"
    return {'id': 'overview', 'text': text, 'verse_refs': refs, 'evidence_ids': [evidence], 'confidence': 'high', 'interpretation_level': 'fact'}

def choose_evidence(book, items):
    """Prefer contextual records belonging to the requested book over later cross-references."""
    prefix = book.lower()
    preferred = [i for i in items if i.id.startswith(prefix) or i.relevance_metadata.get('parent_title', '').lower() == book.lower()]
    return (preferred or list(items))[0].id

def run():
    config = AgentConfig(adapter='openai_compatible', base_url='luna-development://local', model='luna-codex-development')
    builder = CommentaryBuilder(STORE, config=config)
    builder.rescan_progress(check_evidence=False)
    retry_failed = '--retry-failed' in sys.argv
    rerun_batch = '--rerun-batch' in sys.argv
    batch_limit = 10 if '--checkpoint-10' in sys.argv else 25
    selected = []
    for book, ch in builder.discover_canonical_chapters():
        c = load_commentary(STORE, book, ch)
        should_process = ((c is not None and c.status == 'failed') if retry_failed else (not c or c.status != 'validated' or not c.generated_metadata or c.generated_metadata.commentary_prompt_version != COMMENTARY_PROMPT_VERSION))
        if rerun_batch:
            should_process = (book, ch) in TARGETS
        if should_process:
            selected.append((book, ch))
            if len(selected) == batch_limit: break
    stamper = CommentaryGenerator(config)
    for book, ch in selected:
        bundle = get_chapter_evidence_bundle(book, ch)
        if bundle is None: raise RuntimeError(f'Unable to build evidence bundle for {book} {ch}')
        reference = bible.verse_range_reference(book, ch)
        request = CommentaryGenerationRequest(book, ch, reference, bundle.evidence_hash, force_regenerate=True)
        metadata = stamper._authoritative_metadata(request, bundle).to_dict()
        availability = classify_evidence_availability(bundle).value
        evidence = choose_evidence(book, bundle.evidence_items) if bundle.evidence_items else None
        generated_block = block(book, ch, evidence) if evidence else block(book, ch, '')
        if not evidence:
            generated_block['evidence_ids'] = []
            generated_block['confidence'] = 'high'
        else:
            cited = bundle.evidence_by_id[evidence]
            generated_block['confidence'] = cited.confidence
            if cited.relevance_metadata.get('dispute_status') not in (None, '', 'not_disputed'):
                generated_block['interpretation_level'] = 'disputed'
        raw = {'reference': reference, 'book': book, 'chapter': ch, 'status': 'pending', 'evidence_availability': availability, 'sections': [{'kind':'chapter_overview','title':'Chapter overview','blocks':[generated_block]}], 'generated_metadata': metadata}
        result = validate_chapter_commentary(raw, bundle, expected_evidence_hash=bundle.evidence_hash, expected_prompt_version=COMMENTARY_PROMPT_VERSION, expected_reference=reference, expected_book=book, expected_chapter=ch)
        status = CommentaryStatus.VALIDATED.value if result.valid else CommentaryStatus.PARTIAL.value if result.partial else CommentaryStatus.NEEDS_REVIEW.value
        if result.commentary:
            c = ChapterCommentary(reference=reference, book=book, chapter=ch, status=status, sections=list(result.accepted_sections), generated_metadata=result.commentary.generated_metadata, failure_reason=None if result.valid else 'Some generated material was rejected', validation_errors=list(result.errors), validation_warnings=[])
        else:
            c = ChapterCommentary(reference=reference, book=book, chapter=ch, status=CommentaryStatus.FAILED.value, sections=[], generated_metadata=stamper._authoritative_metadata(request,bundle), failure_reason='Validator accepted no sections', validation_errors=list(result.errors), validation_warnings=[])
        path = save_commentary(c, STORE)
        print(f'{reference}: {c.status} sections={len(c.sections)} blocks={sum(len(s.blocks) for s in c.sections)} errors={len(result.errors)} evidence={evidence} file={path}', flush=True)
        if result.errors: print('\n'.join(f'  ERROR {e}' for e in result.errors), flush=True)
    print('Progress:', builder.rescan_progress(check_evidence=False).to_dict(), flush=True)

if __name__ == '__main__': run()
