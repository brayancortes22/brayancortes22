#!/usr/bin/env python3
"""
Script simple para recopilar estadísticas públicas de repositorios de un usuario GitHub
y generar una imagen con gráficas (lenguajes por bytes, conteo de extensiones).

Uso:
  python scripts/generate_stats.py --user brayancortes22 --output assets/code_stats.png

Requiere GITHUB_TOKEN en env (opcional pero recomendado para evitar límites).
"""
import os
import sys
import argparse
import requests
from collections import Counter, defaultdict
import matplotlib.pyplot as plt


def fetch_repos(user, headers):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{user}/repos?per_page=100&page={page}"
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Error fetching repos: {r.status_code} {r.text}")
            break
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def fetch_repo_languages(languages_url, headers):
    r = requests.get(languages_url, headers=headers)
    if r.status_code != 200:
        return {}
    return r.json()


def fetch_tree(owner, repo_name, default_branch, headers):
    # Intenta obtener el árbol recursivo del repo
    url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("tree", [])
    # si falla, devolver vacío
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    print(f"Fetching repos for {args.user}...")
    repos = fetch_repos(args.user, headers)
    print(f"Found {len(repos)} repos")

    languages_total = defaultdict(int)
    ext_counter = Counter()

    for repo in repos:
        name = repo.get("name")
        languages_url = repo.get("languages_url")
        default_branch = repo.get("default_branch") or "main"
        print(f"Processing {name} (branch: {default_branch})")

        # languages (bytes)
        langs = fetch_repo_languages(languages_url, headers)
        for k, v in langs.items():
            languages_total[k] += v

        # tree to count file extensions
        owner = repo.get("owner", {}).get("login")
        tree = fetch_tree(owner, name, default_branch, headers)
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            _, ext = os.path.splitext(path)
            if ext:
                ext_counter[ext.lower()] += 1
            else:
                ext_counter["(no ext)"] += 1

    # Prepare plots
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Top languages
    langs_sorted = sorted(languages_total.items(), key=lambda x: x[1], reverse=True)
    top_langs = langs_sorted[:8]
    langs_names = [l for l, _ in top_langs]
    langs_values = [v for _, v in top_langs]

    # Top extensions
    top_ext = ext_counter.most_common(10)
    ext_names = [e for e, _ in top_ext]
    ext_values = [v for _, v in top_ext]

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    if langs_names:
        axes[0].barh(langs_names[::-1], [v for v in langs_values[::-1]], color="#2b8cbe")
        axes[0].set_title("Top lenguajes por bytes (repos)")
    else:
        axes[0].text(0.5, 0.5, "No se encontraron datos de lenguajes", ha="center")

    if ext_names:
        axes[1].bar(ext_names, ext_values, color="#fdae61")
        axes[1].set_title("Top extensiones (conteo de archivos)")
        axes[1].tick_params(axis='x', rotation=45)
    else:
        axes[1].text(0.5, 0.5, "No se encontraron archivos", ha="center")

    plt.tight_layout()
    fig.suptitle(f"Estadísticas de código — {args.user}", y=1.02)
    plt.savefig(args.output, bbox_inches='tight')
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
