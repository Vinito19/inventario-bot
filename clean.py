#!/usr/bin/env python3
"""
Script de limpieza automática de archivos temporales y artefactos de pruebas.

Uso:
    python clean.py              # Limpieza completa
    python clean.py --tests      # Solo artefactos de tests
    python clean.py --cache      # Solo caches (__pycache__, .pytest_cache)
    python clean.py --all        # Todo (default)
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Patrones de archivos a limpiar
PATTERNS = {
    "pdfs": ["proforma_*.pdf", "proforma_muestra_*.pdf", "proforma_nuevo_*.pdf", "proforma_corregida_*.pdf"],
    "excel": ["inventario_*.xlsx"],
    "backups": ["backup_inventario_*.zip", "backup_inventario_*.db"],
    "db_temp": ["test_inventario.db", "test_inventario.db-*"],
    "images": ["temp/foto_prueba_*.jpg", "temp/*.jpg", "temp/*.png"],
    "logos": ["logo_vch.jpg", "mockup_proforma.*"],
    "cache": ["__pycache__", ".pytest_cache", ".mypy_cache"],
}


def find_files(patterns):
    """Encuentra archivos que coinciden con los patrones."""
    found = []
    for pattern in patterns:
        found.extend(ROOT.rglob(pattern))
    return found


def clean_patterns(patterns, dry_run=False):
    """Elimina archivos/directorios que coinciden con patrones."""
    removed = []
    for pattern in patterns:
        for path in ROOT.rglob(pattern):
            try:
                if path.is_dir():
                    if not dry_run:
                        shutil.rmtree(path)
                    removed.append(f"DIR  {path.relative_to(ROOT)}")
                else:
                    if not dry_run:
                        path.unlink()
                    removed.append(f"FILE {path.relative_to(ROOT)}")
            except Exception as e:
                print(f"  ⚠️  No se pudo eliminar {path}: {e}", file=sys.stderr)
    return removed


def main():
    parser = argparse.ArgumentParser(description="Limpieza automática de artefactos")
    parser.add_argument("--tests", action="store_true", help="Solo artefactos de tests (pdfs, excel, backups, db_temp)")
    parser.add_argument("--cache", action="store_true", help="Solo caches (__pycache__, .pytest_cache)")
    parser.add_argument("--all", action="store_true", help="Todo (default)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se eliminaría")
    args = parser.parse_args()

    if not (args.tests or args.cache or args.all):
        args.all = True

    patterns = []
    if args.tests or args.all:
        patterns.extend(PATTERNS["pdfs"])
        patterns.extend(PATTERNS["excel"])
        patterns.extend(PATTERNS["backups"])
        patterns.extend(PATTERNS["db_temp"])
        patterns.extend(PATTERNS["images"])
    if args.cache or args.all:
        patterns.extend(PATTERNS["cache"])
        patterns.extend(PATTERNS["logos"])

    print(f"{'DRY-RUN: ' if args.dry_run else ''}Limpiando: {', '.join(set(p.split('*')[0].rstrip('_') for p in patterns))}")
    removed = clean_patterns(patterns, dry_run=args.dry_run)

    if removed:
        for item in removed:
            print(f"  {'[DRY-RUN] ' if args.dry_run else ''}[OK] {item}")
        print(f"\nTotal: {len(removed)} elementos {'encontrados' if args.dry_run else 'eliminados'}")
    else:
        print("  (nada que limpiar)")


if __name__ == "__main__":
    main()