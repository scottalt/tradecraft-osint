"""tradecraft CLI (typer)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.console import Console

from tradecraft.analyzers.heuristics import generate_questions
from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.config import AppConfig, default_config_path, load_config
from tradecraft.ethics import is_likely_person_name
from tradecraft.http import HttpClient
from tradecraft.models import Findings, Question, Role, Target
from tradecraft.orchestrator import Orchestrator
from tradecraft.renderers.json import render_json
from tradecraft.renderers.markdown import render_markdown
from tradecraft.renderers.questions import render_questions

app = typer.Typer(
    name="tradecraft",
    help="OSINT tradecraft for the interview chair. Build a dossier on a company.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


def _default_collectors() -> list[Collector]:
    return [FootprintCollector()]


def _infer_company_name(root_url: str) -> str:
    host = urlparse(root_url).hostname or root_url
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return host


@app.command()
def main(  # noqa: PLR0913
    root_url: Annotated[str, typer.Argument(help="Company root URL, e.g. https://acme.com")],
    job: Annotated[str | None, typer.Option(help="Job listing URL")] = None,
    role: Annotated[Role, typer.Option(help="Role focus for the dossier")] = Role.CYBERSECURITY,
    company: Annotated[str | None, typer.Option(help="Override the inferred company name")] = None,
    output: Annotated[Path, typer.Option(help="Output folder root")] = Path("./dossiers"),
    only: Annotated[
        str | None, typer.Option(help="Run only these collectors (comma-separated)")
    ] = None,
    skip: Annotated[
        str | None, typer.Option(help="Skip these collectors (comma-separated)")
    ] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Bypass on-disk cache")] = False,
    json_only: Annotated[
        bool, typer.Option("--json", help="Print raw.json to stdout, no folder")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Log every HTTP request")
    ] = False,
) -> None:
    """Build an interview-prep dossier."""
    company_name = company or _infer_company_name(root_url)
    if is_likely_person_name(company_name):
        err_console.print(
            f"[red]Refusing to run: '{company_name}' looks like a person's name. "
            "tradecraft is for companies only.[/]"
        )
        raise typer.Exit(code=2)

    target = Target(
        company_name=company_name,
        root_url=root_url,
        job_url=job,
        role=role,
    )

    cfg = load_config(default_config_path())
    if no_cache:
        cfg = cfg.model_copy(update={"cache": cfg.cache.model_copy(update={"enabled": False})})

    findings, questions = asyncio.run(_run(target, cfg, only, skip, verbose))

    if json_only:
        typer.echo(render_json(findings, questions))
        return

    folder = output / f"{target.company_slug}-{datetime.now(tz=UTC):%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(render_markdown(findings, questions), encoding="utf-8")
    (folder / "questions.md").write_text(
        render_questions(questions, company_name=company_name), encoding="utf-8"
    )
    (folder / "raw.json").write_text(render_json(findings, questions), encoding="utf-8")
    console.print(f"[green]Dossier written to[/] {folder}")


async def _run(
    target: Target,
    cfg: AppConfig,
    only: str | None,
    skip: str | None,
    verbose: bool,
) -> tuple[Findings, list[Question]]:
    cache_dir: Path
    if cfg.cache.directory:
        cache_dir = Path(cfg.cache.directory)
    else:
        cache_dir = Path.home() / ".cache" / "tradecraft"

    cache = Cache(
        directory=cache_dir,
        default_ttl=cfg.cache.ttl_default_seconds,
        enabled=cfg.cache.enabled,
    )
    target_host = urlparse(str(target.root_url)).hostname
    async with HttpClient(cfg.http, cache, target_host=target_host) as http:
        orch = Orchestrator(_default_collectors(), http=http, cache=cache)
        findings = await orch.run(
            target,
            only=set(only.split(",")) if only else None,
            skip=set(skip.split(",")) if skip else None,
        )
    if verbose:
        for r in findings.results:
            err_console.print(
                f"[dim]{r.name}: {r.duration_ms} ms, signals={[s.value for s in r.signals]}[/]"
            )
    questions = generate_questions(findings)
    return findings, questions


if __name__ == "__main__":
    app()
