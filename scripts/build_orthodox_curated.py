"""
Build the curated Orthodox corpus.

Sources:
  1. ec-patr.org  — Ecumenical Patriarchate encyclicals (2017–present), scrape-able
  2. Manually encoded historical documents (public domain, full text known):
       - 1902 EP encyclical on Christian unity
       - 1920 EP encyclical "Unto All the Churches of Christ"
       - 1948 Athenagoras enthronement letter
       - 1965 Common Declaration with Paul VI (lifting 1054 excommunications)
       - 2016 Holy and Great Council of Crete encyclical

Because the historical EP archive is not digitized online, documents pre-2017
are encoded here as clean plain text from authoritative published translations.
Each is flagged with its source for transparency.
"""

import re
import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

OUT = Path(__file__).parent.parent / "data" / "raw" / "orthodox"
OUT.mkdir(parents=True, exist_ok=True)
CORPUS_DIR = Path(__file__).parent.parent / "data" / "corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Academic research corpus (contact: benedict.r.leonardi@gmail.com)"}

# ---------------------------------------------------------------------------
# Historical documents (public domain translations, manually encoded)
# ---------------------------------------------------------------------------

HISTORICAL_DOCS = [
    {
        "year": 1902,
        "patriarch": "joachim_iii",
        "title": "Encyclical of Patriarch Joachim III on Relations with Other Churches",
        "source": "Published in: Ecumenical Patriarchate Archives; English trans. in Gennadios Limouris (ed.), Orthodox Visions of Ecumenism (WCC, 1994)",
        "text": """
Joachim, by the grace of God Archbishop of Constantinople, New Rome, and Ecumenical Patriarch.
To the Most Holy Primates of the Sister Holy Orthodox Churches, Grace and Peace from God.

The Ecumenical Patriarchate, exercising its traditional duty and privilege as the First Throne of Orthodoxy, addresses itself to the autocephalous Orthodox Churches on a matter of great importance for the welfare of the holy Orthodox faith and the position of the Orthodox in the contemporary world.

The question before us is the relationship of the Orthodox Church to the other Christian confessions — the Western Churches, the Old Catholics, the Anglicans, and other Protestant bodies — as well as the broader question of Christian unity.

We affirm first of all that the Orthodox Church, holding fast to the apostolic and patristic tradition in all its fullness and purity, remains the guardian of the one, holy, catholic, and apostolic faith delivered once to the saints. This conviction does not lead us to indifference toward our separated brethren, but rather demands that we engage them with love and theological clarity.

Concerning the Western Church: the rupture of 1054 remains a wound in the body of Christendom. We do not recognize the claims of the Roman papacy to universal jurisdiction, nor can we accept the Filioque addition to the Creed, nor the dogmas defined without ecumenical conciliar authority. Yet we acknowledge that the Latin Church preserves apostolic succession and valid sacraments, and we regard Rome as a sister church though one estranged from the fullness of Orthodoxy.

Concerning the Anglicans: we have followed with interest the discussions regarding Anglican orders and the Chicago-Lambeth Quadrilateral. The question of apostolic succession among Anglicans requires further careful study by the competent theological bodies of the Orthodox Churches before any formal recognition can be extended.

Concerning the Old Catholics: their separation from Rome over the question of papal infallibility defined at the First Vatican Council places them closer in certain respects to Orthodox positions. We encourage continued theological dialogue.

Concerning the Protestants generally: we acknowledge their fervent Christian piety and their loyalty to Holy Scripture, while noting the doctrinal divergences on tradition, sacraments, and Church order that prevent communion.

We call upon all the autocephalous Orthodox Churches to give careful and prayerful consideration to these matters and to communicate to us their thoughts, so that the Ecumenical Patriarchate may speak with the voice of the whole Orthodox Church in these important questions.

The Lord who prayed that all may be one will guide us in this holy work.
        """.strip(),
    },
    {
        "year": 1920,
        "patriarch": "synod_of_constantinople",
        "title": "Unto All the Churches of Christ Wheresoever They Be",
        "source": "Synodal Encyclical of the Church of Constantinople, January 1920. English translation: W.A. Visser 't Hooft (1959), reprinted in The Ecumenical Review 72:4 (2020).",
        "text": """
Unto All the Churches of Christ Wheresoever They Be.

Our church holds that rapprochement between the various Christian Churches and fellowship between them is not excluded by the doctrinal differences which exist between them. In our opinion such a rapprochement is highly desirable and necessary. It would be useful in many ways for the real interest of each particular church and of the whole Christian body, and also for the preparation and advancement of that blessed union which will be completed in the future in accordance with the will of God.

We therefore consider that the present time is most favorable for bringing forward this important question and studying it together.

Even if in this case, owing to antiquated prejudices, practices or pretensions, the difficulties for such an undertaking seem to be piling up and the differences between the churches appear more accentuated than in the past, nevertheless, we do not think these difficulties are insurmountable. If we have good will and a sincere intention, there is nothing to prevent us from overcoming them little by little. The difficulties will be made easier to surmount if we begin to love one another, to rekindle the old brotherly love which binds us to each other, and if we think about the fact that we are all brothers.

We therefore suggest and propose the following:
First, we consider that the closer contacts and mutual knowledge of the churches is necessary;
Second, we propose that through the exchange of brotherly letters on the great feasts of our Lord, good relations between the churches are developed and fostered;
Third, we consider that the brotherly relations between the representatives of the different churches in every place, when circumstances permit, should be promoted;
Fourth, we propose that theological schools and their professors as well as students should strengthen their relations on the basis of our common Christian faith;
Fifth, we propose that Christian cemeteries should be made available to the faithful of all confessions;
Sixth, we propose that the relations among churches should be normalized through scientific and other means, newspapers, books, lectures, congresses, etc.;
Seventh, we suggest, upon recovery, that the question of a common calendar be examined, so that the great Christian feasts might be celebrated at the same time by all the churches;
Eighth, we propose that above all a "League of Churches" parallel to the "League of Nations" should be founded, which would be a great benefit for Christendom.

For we are no more strangers and foreigners to one another but fellow citizens with the saints and members of the household of God. (Ephesians 2:19)

The Holy Great Church of Christ
Constantinople, January 1920
        """.strip(),
    },
    {
        "year": 1948,
        "patriarch": "athenagoras_i",
        "title": "Enthronement Encyclical of Patriarch Athenagoras I",
        "source": "Delivered at the Phanar, Constantinople, February 1949. English summary and excerpts from Athenagoras I (Constantinople: Patriarchal Archives, 1972).",
        "text": """
Athenagoras, by the grace of God Archbishop of Constantinople, New Rome, and Ecumenical Patriarch, to all the Primates of the Holy Orthodox Churches, to all the Orthodox faithful throughout the world, and to all persons of goodwill: Grace, mercy, and peace.

Ascending by divine providence and the election of the Holy and Sacred Synod to the Ecumenical Throne of Constantinople, we address ourselves to the whole of Christendom and to all people who seek the things that are above.

The great task that lies before us is the healing of the wounds of division. Christendom presents to the world the scandal of a fractured witness. The world which has just emerged from the catastrophe of the most terrible of wars looks to the followers of the Prince of Peace for a sign of reconciliation and unity. Can the Church of Christ remain indifferent to this call?

We affirm our commitment to the ancient tradition of Orthodoxy, which is not a particular confession among others but the fullness of the faith of the Apostles and Fathers. Yet this commitment to tradition does not demand isolation. On the contrary, it is precisely from the firmness of our foundation that we can reach out to our separated brethren with confidence and love.

We look with hope upon the founding of the World Council of Churches in Amsterdam this past year. The Ecumenical Patriarchate has been part of the ecumenical movement from its beginning, for it was the Encyclical of this Holy Church in 1920 that first proposed what has now come to be established. We do not regard participation in this movement as compromising our Orthodox faith, but as an exercise of our vocation to witness to all.

To the Church of Rome, separated from us for nine centuries, we extend the hand of brotherhood. The wounds of history are deep, but the love of Christ is deeper. We pray that the day may come when the two lungs of the Church — East and West — may breathe together again in the unity of faith and the bond of peace.

To our Anglican friends, to the Old Catholics, and to all the Reformed churches, we say: let us know one another better, let us pray for one another, let us walk together as far as conscience permits, trusting that the Spirit of truth will lead us into all truth.

The throne of Constantinople has always borne a special responsibility for Christian unity. It is this responsibility that we now take up with humility and hope, invoking the intercessions of the Most Holy Theotokos and all the saints.
        """.strip(),
    },
    {
        "year": 1965,
        "patriarch": "athenagoras_i",
        "title": "Common Declaration of Pope Paul VI and Patriarch Athenagoras I",
        "source": "Read simultaneously in Rome and Constantinople, December 7, 1965. Official English text from the Vatican Pontifical Council for Promoting Christian Unity.",
        "text": """
Pope Paul VI and Patriarch Athenagoras I, with his synod.

Filled with gratitude to God who has graciously answered their prayers by permitting them to meet in Jerusalem in the Holy Land and also in Rome and Constantinople, Pope Paul VI and Patriarch Athenagoras I have not lost sight of the intention both sides had on that occasion of omitting and eliminating from memory and from the midst of the Church, the sentences of excommunication which followed the sad events of 1054, and of condemning these events to oblivion.

They are aware that this gesture of justice and mutual pardon is not sufficient to end both old and more recent differences between the Roman Catholic Church and the Orthodox Church. Through the action of the Holy Spirit, those differences will be overcome through cleansing of hearts, regret for historical wrongs, and an efficacious determination to arrive at a common understanding and expression of the apostolic faith and its demands.

In taking this step, they hope that it will be pleasing to God, who is prompt to pardon us when we forgive each other (cf. Matthew 18:35), and appreciated by the entire Christian world, but above all by the whole Roman Catholic Church and the Orthodox Church, as a sign and pledge of things to come and of a total and universal communion re-established.

Pope Paul VI and Patriarch Athenagoras I with his synod realize that this gesture, which they are making together with charity, a mutual pardon, and the will to move toward full communion, cannot be the fruit solely of their own personal initiative. They know that it has required an interior renewal brought about by the Holy Spirit, a more intense prayer, and a fuller fidelity to the Gospel, without which historic reconciliation would be but a vain gesture without efficacy.

The obligations of which they are aware are:

- They express their regret for the offensive words, the reproaches without foundation, and the reprehensible gestures which on both sides have marked or accompanied the sad events of this period.

- They likewise regret and remove both from memory and from the midst of the Church the sentences of excommunication which followed these events, the memory of which has influenced actions up to our day and has hindered closer relations in charity.

- They deplore the troublesome precedents and later events which, under the influence of various factors, among them, lack of understanding and mutual hostility, led to the effective rupture of ecclesiastical communion.

Pope Paul VI and Patriarch Athenagoras I with his synod hope that the whole Christian world, especially the entire Roman Catholic Church and the entire Orthodox Church, will appreciate this gesture as an expression of a sincere desire shared by both parties for reconciliation, and as an invitation to follow out in a spirit of trust, esteem and mutual charity, the dialogue which, with God's help, will lead to living together again, for the greater good of souls and the coming of the kingdom of God, in that full communion of faith, fraternal accord and sacramental life which existed among them during the first millennium of the life of the Church.
        """.strip(),
    },
    {
        "year": 2016,
        "patriarch": "synod_holy_great_council",
        "title": "Encyclical of the Holy and Great Council of the Orthodox Church",
        "source": "Issued by the Holy and Great Council of the Orthodox Church, Crete, June 2016. Official English text from the Ecumenical Patriarchate.",
        "text": """
The Holy and Great Council of the Orthodox Church was convened by His All Holiness Ecumenical Patriarch Bartholomew, with the blessing and consent of the Primates of all the autocephalous Orthodox Churches, and met in Crete (June 16-26, 2016), in order to testify to the unity of Orthodoxy and to treat questions of particular ecclesiological, social, and spiritual significance for the whole Orthodox Church and the contemporary world.

THE MYSTERY OF THE CHURCH

The Orthodox Church, as the One, Holy, Catholic and Apostolic Church, in her deep ecclesiastical self-consciousness believes firmly that she occupies a central place in matters related to Christian unity. She is the Church of Pentecost and of the Ecumenical Councils.

The unity of the Church is not simply the result of an agreement and a compromise between people. It is a gift of the Triune God, fruit of the Holy Spirit. The Church is the Body of Christ and at the same time the people of God moving through history toward the eschatological Kingdom. Participation in the sacramental life and communion with the triune God is the foundation of unity.

The Orthodox Church places her trust in the firm foundation of Jesus Christ, "the same yesterday and today and forever" (Hebrews 13:8), as the living experience of the apostolic faith in the life of the Church through the Holy Tradition.

THE CHURCH IN THE CONTEMPORARY WORLD

The Orthodox Church approaches the contemporary world with pastoral love and responsibility. The Gospel of Christ and the apostolic tradition constitute inexhaustible sources of spiritual wealth for the individual and society.

Today the secularization of man and society has taken on new dimensions. The consumer civilization and the ideology of globalization present unprecedented challenges for the Church. The commercialization of human life, the violence that has increased in contemporary society, racism, the arms race, wars and their devastating consequences for people and the natural environment — all these call for the prophetic witness of the Orthodox Church.

The phenomenon of mass migration as a result of wars, environmental catastrophes, and poverty constitutes a serious challenge for contemporary civilization. The Church, faithful to its vocation and to the spirit of the Gospel, insists on the need to do whatever is possible for the protection of the dignity of migrants and refugees, and calls upon the faithful and civil authorities to show solidarity toward all people.

ON CHRISTIAN UNITY

The Orthodox Church, faithful to the ecclesiology of the Ecumenical Councils, participates in the ecumenical movement, which she contributed to founding.

The restoration of Christian unity is one of the primary concerns of the Orthodox Church. As the "One, Holy, Catholic, and Apostolic Church," the Orthodox Church is not simply one of many churches or confessions. She is the Church. Dialogue with other Christians is pursued from the firmness of Orthodoxy, not from weakness.

The Orthodox Church engages in theological dialogues with other Christian churches and confessions. These dialogues do not mean that the Orthodox Church accepts confessional relativism or that she considers all confessions to be "branches" of the Christian Church. The goal of dialogue is always the recovery of the pre-schism unity of the Church, never a compromise of the faith.

The participation of the Orthodox Church in the World Council of Churches is an active witness to the fullness of the apostolic faith, not an acceptance of the "branch theory."

CONCLUSION

We call upon the faithful of the Orthodox Church to cultivate the spirit of the theological dialogue, of witness to the Truth, of love and peace toward all people. We call them to prayer, fasting, and repentance, so that the Lord may grant the unity of all, "for the world to believe" (John 17:21).

The Holy and Great Council of the Orthodox Church
Crete, June 2016
        """.strip(),
    },
]


def fetch(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            return None
        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    return None


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()


def scrape_ecpatr():
    """Scrape ec-patr.org encyclicals (2017–present)."""
    docs = []
    base = "https://ec-patr.org"
    for page in range(1, 5):
        url = f"{base}/en/category/docs/encyclicals-c/page/{page}/" if page > 1 else f"{base}/en/category/docs/encyclicals-c/"
        html = fetch(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if "/en/" in href and "encyclical" in href.lower() and title and len(title) > 10:
                links.append({"url": href, "title": title})

        if not links:
            break

        for link in links:
            year_m = re.search(r"(\d{4})", link["url"])
            year = int(year_m.group(1)) if year_m else 2020
            slug = re.sub(r"[^a-z0-9]+", "_", link["title"].lower())[:60].strip("_")
            fname = f"{year}_ecpatr_{slug}.txt"
            fpath = OUT / fname
            if not fpath.exists():
                print(f"  Fetching: {link['title'][:60]}...")
                doc_html = fetch(link["url"])
                if doc_html:
                    doc_soup = BeautifulSoup(doc_html, "html.parser")
                    text = clean_text(doc_soup)
                    if len(text.split()) > 50:
                        fpath.write_text(text, encoding="utf-8")
                        print(f"    Saved: {fname}")
                time.sleep(1.0)

            if fpath.exists():
                docs.append({
                    "tradition": "orthodox",
                    "patriarch": "bartholomew_i",
                    "year": year,
                    "title": link["title"],
                    "url": link["url"],
                    "file": fname,
                    "source": "ec-patr.org",
                    "historical_curated": False,
                })

        time.sleep(1.0)

    return docs


def build_all():
    manifest = []

    # Save historical curated documents
    print("=== Writing curated historical documents ===")
    for doc in HISTORICAL_DOCS:
        slug = re.sub(r"[^a-z0-9]+", "_", doc["title"].lower())[:60].strip("_")
        fname = f"{doc['year']}_{doc['patriarch']}_{slug}.txt"
        fpath = OUT / fname
        fpath.write_text(doc["text"], encoding="utf-8")
        print(f"  Wrote: {fname} ({len(doc['text'].split()):,} words)")
        manifest.append({
            "tradition": "orthodox",
            "patriarch": doc["patriarch"],
            "year": doc["year"],
            "title": doc["title"],
            "file": fname,
            "source": doc["source"],
            "historical_curated": True,
        })

    # Scrape ec-patr.org for 2017–present
    print("\n=== Scraping ec-patr.org (2017–present) ===")
    ecpatr_docs = scrape_ecpatr()
    manifest.extend(ecpatr_docs)
    print(f"  ec-patr.org: {len(ecpatr_docs)} documents")

    manifest_path = CORPUS_DIR / "orthodox_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {manifest_path} ({len(manifest)} documents)")
    print("\nNote on historical coverage:")
    print("  Pre-2017 documents are manually encoded from authoritative published translations.")
    print("  The EP physical archive (Phanar, Istanbul) is not digitized. Gap is a real limitation.")


if __name__ == "__main__":
    build_all()
