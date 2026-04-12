from .geopolitics import GeopoliticsSkill
from .markets import MarketsSkill
from .technology_ai import TechnologyAISkill


def build_skill_registry():
    return {
        "geopolitics": GeopoliticsSkill(),
        "technology_ai": TechnologyAISkill(),
        "markets": MarketsSkill(),
    }
