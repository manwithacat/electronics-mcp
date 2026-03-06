import pytest
from electronics_mcp.core.database import Database
from electronics_mcp.engines.knowledge.manager import KnowledgeManager
from electronics_mcp.engines.knowledge.topology import TopologyExplainer
from electronics_mcp.engines.knowledge.design_guide import DesignGuide


@pytest.fixture
def km(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize(seed=True)
    return KnowledgeManager(db)


@pytest.fixture
def db_seeded(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize(seed=True)
    return db


class TestKnowledgeManager:
    def test_learn_and_get_topic(self, km):
        topic_id = km.learn_pattern(
            category="topology",
            topic="voltage_divider",
            title="Voltage Divider",
            content="A voltage divider uses two resistors to produce a fraction of the input voltage.",
            formulas=[{"name": "Vout", "expression": "Vin * R2 / (R1 + R2)"}],
            related_topics=["resistor_networks"],
        )
        assert topic_id

        article = km.get_topic("voltage_divider")
        assert article is not None
        assert article["title"] == "Voltage Divider"
        assert len(article["formulas"]) == 1
        assert article["formulas"][0]["name"] == "Vout"

    def test_search_fts(self, km):
        km.learn_pattern(
            category="filter",
            topic="low_pass_rc",
            title="RC Low-Pass Filter",
            content="An RC low-pass filter attenuates signals above the cutoff frequency.",
            formulas=[{"name": "fc", "expression": "1 / (2 * pi * R * C)"}],
        )
        results = km.search("low-pass cutoff frequency")
        assert len(results) > 0
        assert "low_pass_rc" in results[0]["topic"]

    def test_search_with_category(self, km):
        km.learn_pattern("filter", "hp_rc", "HP Filter", "High-pass filter content.")
        km.learn_pattern(
            "amplifier", "common_emitter", "CE Amp", "Common emitter amplifier."
        )

        filter_results = km.search("filter", category="filter")
        assert all(r["category"] == "filter" for r in filter_results)

    def test_get_formulas(self, km):
        km.learn_pattern(
            "topology",
            "wheatstone_bridge",
            "Wheatstone Bridge",
            "Used for precision measurements.",
            formulas=[
                {"name": "balance", "expression": "R1*R3 = R2*R4"},
                {"name": "Vout", "expression": "Vs * (R3/(R3+R4) - R2/(R1+R2))"},
            ],
        )
        formulas = km.get_formulas("wheatstone_bridge")
        assert len(formulas) == 2

    def test_component_info(self, km):
        info = km.component_info("resistor")
        assert info["type"] == "resistor"
        assert len(info["categories"]) > 0


class TestTopologyExplainer:
    def test_explain_known_topic(self, db_seeded):
        km = KnowledgeManager(db_seeded)
        km.learn_pattern(
            "topology",
            "common_emitter",
            "Common Emitter Amplifier",
            "The common emitter is a basic BJT amplifier topology providing voltage gain.",
            formulas=[{"name": "Av", "expression": "-gm * Rc"}],
        )
        explainer = TopologyExplainer(db_seeded)
        result = explainer.explain("common_emitter")
        assert result["explanation"] is not None
        assert len(result["formulas"]) > 0

    def test_explain_via_search(self, db_seeded):
        km = KnowledgeManager(db_seeded)
        km.learn_pattern(
            "filter",
            "butterworth",
            "Butterworth Filter",
            "Maximally flat magnitude response filter design.",
        )
        explainer = TopologyExplainer(db_seeded)
        result = explainer.explain("butterworth")
        assert result["explanation"] is not None

    def test_list_topologies(self, db_seeded):
        km = KnowledgeManager(db_seeded)
        km.learn_pattern("topology", "t1", "Topic 1", "Content 1")
        km.learn_pattern("circuit", "t2", "Topic 2", "Content 2")
        explainer = TopologyExplainer(db_seeded)
        topics = explainer.list_topologies()
        assert len(topics) >= 2


class TestDesignGuide:
    def test_generate_filter_guide(self, db_seeded):
        km = KnowledgeManager(db_seeded)
        km.learn_pattern(
            "filter",
            "low_pass_filter",
            "Low-Pass Filter Design",
            "1. Choose cutoff frequency\n2. Select R value\n3. Calculate C = 1/(2*pi*R*fc)",
            formulas=[{"name": "fc", "expression": "1/(2*pi*R*C)"}],
        )
        guide = DesignGuide(db_seeded)
        result = guide.generate("low_pass_filter")
        assert len(result["steps"]) > 0
        assert len(result["formulas"]) > 0
        assert len(result["component_suggestions"]) > 0  # "filter" maps to R, C, L

    def test_generate_with_requirements(self, db_seeded):
        guide = DesignGuide(db_seeded)
        result = guide.generate(
            "amplifier",
            requirements={
                "frequency": "1kHz",
                "voltage": "12V",
            },
        )
        assert any("1kHz" in n for n in result["notes"])
        assert any("12V" in n for n in result["notes"])
