"""
QuantumHub - A research platform for quantum computing papers and hard project
implementations from institutions, companies, and independent organisations.

Built by Sandesh Dhital.
"""

__version__ = "1.0.0"
__author__ = "Sandesh Dhital"

__all__ = [
    "Paper",
    "PaperRepository",
    "Project",
    "ProjectRepository",
    "__version__",
]


def __getattr__(name: str):
    """Import repository symbols lazily to keep the package import light."""
    if name in ("Paper", "PaperRepository"):
        from quantumhub.papers import Paper, PaperRepository

        return {"Paper": Paper, "PaperRepository": PaperRepository}[name]
    if name in ("Project", "ProjectRepository"):
        from quantumhub.projects import Project, ProjectRepository

        return {"Project": Project, "ProjectRepository": ProjectRepository}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
