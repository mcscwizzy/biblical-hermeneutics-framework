"""Reviewed Wikimedia Commons media for the complete archaeology corpus.

The file identifiers and caption context are reviewed in
``data_sources/archaeology/full-coverage-wikimedia-manifest.json``.  This
snapshot keeps the verified attribution and license metadata available to the
application without making an API request during database initialization.
"""

from __future__ import annotations

from urllib.parse import quote


_REVIEWED_MEDIA = [
    ("wm-al-yahudu-tablets", "al-yahudu-tablets", "Al-Yahudu Tablets2.jpg", "Al-Yahudu tablets, documentary evidence for Judean life in Babylonia.", "עמית אבידן", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-amarna-letters", "amarna-letters", "Five Amarna letters on display at the British Museum, LondonA.jpg", "Amarna letters displayed at the British Museum.", "Osama Shukir Muhammed Amin FRCP(Glasg)", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-avaris-excavations", "avaris-excavations", "Tell el-daba04.jpg", "View of the Tell el-Dab'a / Avaris archaeological site.", "Didia", "Own work (David Schmid)", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-beni-hasan-caravan", "beni-hasan-asiatic-caravan", "Asiatics with lyre Beni Hasan.jpg", "Beni Hasan painting of Asiatic visitors with a lyre.", "A.D. Riddle", "A.D. Riddle photograph of a two-dimensional public-domain object (PD-Art).", "Public domain", "", "public_domain", True),
    ("wm-bethsaida-site", "bethsaida-identification", "Bethsaida - Beit Saida03.jpg", "Archaeological remains at et-Tell, one proposed Bethsaida location.", "Hoshvilim", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-corinth-bema", "corinth-bema", "Ancient Corinth - Bema.jpg", "The bema in ancient Corinth.", "Ploync", "Own work", "CC BY 3.0", "https://creativecommons.org/licenses/by/3.0", "cc_by", True),
    ("wm-corinth-site", "corinth-excavations", "Archaeological site of Corinth, entrance, 202776.jpg", "Archaeological site of ancient Corinth.", "Zde", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-ebla-palace-g", "ebla-archives", "Ebla Palazzo G - GAR - 9-01.JPG", "Royal Palace G at Ebla, where the archive was discovered.", "Gianfranco Gazzetti", "Gruppo Archeologico Romano / Connected Open Heritage", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-ekron-dedicatory-inscription", "ekron-dedicatory-inscription", "Dedicatory Stone Inscription, Ekron, 7th Century BC (43167220572).jpg", "Ekron royal dedicatory inscription.", "Gary Todd from Xinzheng, China", "Dedicatory Stone Inscription, Ekron, 7th Century BC", "CC0", "http://creativecommons.org/publicdomain/zero/1.0/deed.en", "cc0", True),
    ("wm-ekron-excavations", "ekron-excavations", "Ekron001.jpg", "Archaeological remains at Ekron (Tel Miqne).", "Ori~", "Own work", "Attribution", "", "other_redistributable", False),
    ("wm-ephesus-theater", "ephesus-theater", "Ephesus great theater.jpg", "Great Theater of Ephesus.", "Ad Meskens", "Own work", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-erastus-inscription", "erastus-inscription", "Erastus Inschrift.jpg", "Erastus inscription in ancient Corinth.", "Ktiv", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-galilee-boat", "galilee-fishing-boat", "Galileeboat.jpg", "First-century Galilee fishing boat in the Yigal Allon Museum.", "User:Jack1956", "Own work", "Public domain", "", "public_domain", True),
    ("wm-gezer-calendar", "gezer-calendar", "Reproduction of the Gezer calendar.jpg", "Reproduction of the Gezer Calendar at Tel Gezer.", "Ian Scott", "Flickr: Reproduction of the Gezer calendar", "CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0", "cc_by_sa", True),
    ("wm-jehoiachin-ration-tablet", "jehoiachin-ration-tablets", "Jehoiachin Ration Tablet detail.jpg", "Detail of the Jehoiachin Ration Tablet.", "Scallaham", "Cropped from File:Jehoiachin Ration Tablet.JPG", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-jerusalem-destruction-context", "jerusalem-babylonian-destruction", "South wall (4107570886).jpg", "City of David excavation context; this is a site view, not a photograph of the destruction deposit itself.", "Joe Goldberg", "South wall", "CC BY 2.0", "https://creativecommons.org/licenses/by/2.0", "cc_by", True),
    ("wm-jerusalem-mikveh", "jerusalem-mikvaot", "Mikveh P8050081.JPG", "Archaeological mikveh in Jerusalem's Herodian Quarter.", "Deror avi", "Own work", "Attribution", "", "other_redistributable", False),
    ("wm-jewish-stone-vessels", "jewish-stone-vessels", "Stone Vessels cave.jpg", "Stone-vessel production cave in the Jerusalem area.", "Owenglyndur", "Own work", "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0", "cc_by", True),
    ("wm-khirbet-qeiyafa-fortress", "khirbet-qeiyafa-fortress", "Excavations at Khirbet Qeiyafa.jpg", "Excavations at the Khirbet Qeiyafa fortified site.", "Davidbena", "Own work", "CC0", "http://creativecommons.org/publicdomain/zero/1.0/deed.en", "cc0", True),
    ("wm-khirbet-qeiyafa-ostracon", "khirbet-qeiyafa-ostracon", "Khirbet Qeiyafa Ostracon.jpg", "Illustrative rendering of the Khirbet Qeiyafa Ostracon; readings remain debated.", "MichaelNetzer", "Own work", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-kuntillet-ajrud", "kuntillet-ajrud-inscriptions", "Ajrud.jpg", "Painted pithos fragment from Kuntillet Ajrud.", "Unknown author", "Kuntillet Ajrud", "Public domain", "", "public_domain", True),
    ("wm-lachish-destruction-context", "lachish-destruction-level", "LachishRamp053011.jpg", "Lachish site context, including the Assyrian siege ramp; not a direct image of Level III's destruction deposit.", "Wilson44691", "Own work", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-lachish-siege-ramp", "lachish-siege-ramp", "LachishRamp053011.jpg", "Assyrian siege ramp at Lachish.", "Wilson44691", "Own work", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-laodicea-aqueduct", "laodicea-water-system", "Laodicea Aqueduct tower.jpg", "Aqueduct tower at Laodicea on the Lycus.", "Rjdeadly", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-mari-tablets", "mari-tablets", "Cuneiform Clay Tablets from Amorite Kingdom of Mari, 1st Half of 2nd Mill. BC.jpg", "Cuneiform tablet from the Amorite kingdom of Mari.", "Gary Todd", "Flickr source via Wikimedia Commons", "CC0", "http://creativecommons.org/publicdomain/zero/1.0/deed.en", "cc0", True),
    ("wm-nazareth-archaeology", "nazareth-archaeology", "Sisters of Nazareth Convent (Nazareth) archaeological site, 2019 (03).jpg", "Archaeological remains beneath the Sisters of Nazareth Convent.", "Bahnfrend", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-pergamum-imperial-cult", "pergamum-imperial-cult", "Pergamum.jpg", "Archaeological view of Pergamum's acropolis.", "Murat Beşbudak", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-philadelphia-city", "philadelphia-city-archaeology", "Alaşehir Church of St. John 2.jpg", "Later archaeological remains at Alaşehir (ancient Philadelphia); visual context only.", "simonjenkins' photos / Wolfymoza", "Church of St John", "CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0", "cc_by_sa", True),
    ("wm-philippi-forum", "philippi-forum", "Philippi -- Agora 07.jpg", "Roman forum / agora remains at Philippi.", "Explorer1940", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-philistine-bichrome-pottery", "philistine-bichrome-pottery", "Bichrome pottery.jpg", "Philistine bichrome pottery.", "Peter Hagyo-Kovacs", "Own work", "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "cc_by_sa", True),
    ("wm-pi-ramesses-qantir", "pi-rameses-qantir", "Kolossalstatue Qantir.JPG", "Colossal statue from Qantir / Pi-Ramesses.", "Iri-en-achti", "Self-photographed", "Public domain", "", "public_domain", True),
    ("wm-qumran-settlement", "qumran-settlement", "141218 remains of a settlement at qumran PikiWiki Israel.jpg", "Settlement remains at Qumran.", "רוני קניגסברג", "PikiWiki Israel", "CC BY 2.5", "https://creativecommons.org/licenses/by/2.5", "cc_by", True),
    ("wm-shechem-excavations", "shechem-middle-bronze", "Ausgrabung von Sichem 1961.jpg", "Excavations at ancient Shechem in 1961.", "Abubiju", "Own work", "CC0", "http://creativecommons.org/publicdomain/zero/1.0/deed.en", "cc0", True),
    ("wm-silwan-tombs", "silwan-tombs", "Silwan tombs.jpg", "Iron Age tombs at Silwan.", "Jprg1966", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-smyrna-agora", "smyrna-roman-city", "Agora in the city of Izmir.jpg", "Agora remains in ancient Smyrna / İzmir.", "Helen Owl", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-tel-dan-cultic-complex", "tel-dan-cultic-complex", "Tel-dan-kultplatz-d-altar.JPG", "Cultic altar complex at Tel Dan.", "Mboesch", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-artemis-ephesus", "temple-artemis-ephesus", "TR.IZ.Selcuk Ephesus 2011-10-04 Temple-of-Artemis 07 3x2-R 5K.jpg", "Temple of Artemis archaeological remains at Ephesus.", "Roy Egloff", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
    ("wm-thyatira-columns", "thyatira-trade-and-inscriptions", "Columns of Thiatira.jpg", "Roman-period columns at Thyatira.", "Pragdon", "Own work", "CC0", "http://creativecommons.org/publicdomain/zero/1.0/deed.en", "cc0", True),
    ("wm-timnah-tel-batash", "timnah-excavations", "Tel-Batash-654.jpg", "Archaeological remains at Tel Batash, identified with Timnah by many scholars.", "Bukvoed", "Own work", "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0", "cc_by", True),
    ("wm-ugarit-site", "ugarit-ras-shamra", "Ugarit ras shamra.jpg", "Archaeological remains at Ugarit / Ras Shamra.", "Mbenoist", "Transferred from French Wikipedia to Commons", "CC BY-SA 3.0", "http://creativecommons.org/licenses/by-sa/3.0/", "cc_by_sa", True),
    ("wm-ugaritic-baal-cycle", "ugaritic-baal-cycle", "Mythological poem Baal death AO16641 AO16642 mp3h8918.jpg", "Ugaritic mythological tablet associated with the Baal Cycle.", "Rama", "Own work", "CC BY-SA 2.0 fr", "https://creativecommons.org/licenses/by-sa/2.0/fr/deed.en", "cc_by_sa", True),
    ("wm-yehud-falcon-coin", "yehud-coinage", "Yehud-falcon-coin.jpg", "Persian-period Yehud coin with falcon imagery.", "Y-barton", "Own work", "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "cc_by_sa", True),
]


def _commons_file_url(filename: str) -> str:
    return f"https://commons.wikimedia.org/wiki/File:{quote(filename.replace(' ', '_'))}"


def _commons_image_url(filename: str) -> str:
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}"


ARCHAEOLOGY_FULL_COVERAGE_MEDIA = [
    {
        "id": media_id,
        "archaeology_item_id": item_id,
        "title": filename,
        "caption": caption,
        "source_url": _commons_file_url(filename),
        "image_url": _commons_image_url(filename),
        "thumbnail_url": f"{_commons_image_url(filename)}?width=1200",
        "creator": creator,
        "institution": institution,
        "license_id": license_id,
        "license_url": license_url,
        "rights_status": rights_status,
        "can_redistribute": redistributable,
        "can_cache": redistributable,
        "can_modify": redistributable,
        "source_record_id": f"File:{filename}",
    }
    for (
        media_id, item_id, filename, caption, creator, institution, license_id,
        license_url, rights_status, redistributable,
    ) in _REVIEWED_MEDIA
]
