from morning_briefs.skills.base import KeywordSubSkill


class FrontierAISubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="frontier_ai",
            description="Model releases, agents, benchmarks, foundation-model strategy, and AI products.",
            keywords=(
                "ai",
                "artificial intelligence",
                "model",
                "agent",
                "llm",
                "openai",
                "anthropic",
                "google",
                "microsoft",
                "benchmark",
            ),
            weight=1.2,
        )


class ChipsComputeSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="chips_compute",
            description="Semiconductors, GPUs, data centers, cloud infrastructure, and energy demand.",
            keywords=(
                "chip",
                "chips",
                "semiconductor",
                "gpu",
                "nvidia",
                "amd",
                "data center",
                "cloud",
                "compute",
                "tsmc",
            ),
            weight=1.05,
        )


class CyberPolicySubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="cyber_policy",
            description="Cybersecurity incidents, regulation, privacy, safety, and platform governance.",
            keywords=(
                "cyber",
                "hack",
                "breach",
                "privacy",
                "regulation",
                "regulator",
                "safety",
                "policy",
                "antitrust",
                "security",
            ),
            weight=1.0,
        )
