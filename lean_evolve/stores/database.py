from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from lean_evolve.stores.island import Island
from lean_evolve.utils import read_json, save_json


class Database:
    """A collection of islands, each containing multiple programs."""

    path: Path
    data: Dict[str, Any]
    n_islands: int
    n_programs: int

    def __init__(
        self,
        path: Path,
        data: Dict[str, Any],
        n_islands: int = 1,
        n_programs: int = 0,
        max_island_size: int = 1,
    ):
        """Initialize the population with its directory path and configuration."""
        self.path = path
        self.data = data
        self.n_islands = n_islands
        self.n_programs = n_programs
        self.max_island_size = max_island_size
        self.metadata_path = self.path / "metadata.json"
        self.path.mkdir(parents=True, exist_ok=True)

        if not self.metadata_path.exists():
            self._save_data()
        # dirs = [p.name for p in self.path.iterdir() if p.is_dir()]
        # if len(dirs) > 0:
        #     data = {
        #         "islands": [
        #             {
        #                 "island_id": 0,
        #                 "path": str(self.path / p.name),
        #             }
        #             for p in self.path.iterdir()
        #             if p.is_dir()
        #         ],
        #     }
        #     self._save_data(data)

    def _get_new_id(self) -> int:
        """Return the next available island ID."""
        if self.get_islands():
            return max(island.id() for island in self.get_islands()) + 1
        return 0

    def create_new_island(self) -> Island:
        """Create a new island, generate programs inside it, and return it."""
        island_id = self._get_new_id()
        island_path = self.path / f"island_{island_id}"
        meta = self._load_data()
        meta["islands"].append(
            {
                "island_id": island_id,
                "path": str(island_path),
            }
        )
        self._save_data(meta)
        return Island(path=island_path, data=self.data, max_size=self.max_island_size)

    def get_islands(self) -> List[Island]:
        """Return all islands stored in the population directory."""

        if self.metadata_path.exists():
            meta = self._load_data()
            return [
                Island(Path(item["path"]), self.data, self.max_island_size)
                for item in meta["islands"]
            ]

    def _load_data(self) -> dict:
        """Load metadata.json."""
        with open(self.metadata_path, "r") as f:
            return json.load(f)

    def _save_data(self, data: Optional[dict] = None):
        """Write metadata.json to disk."""
        if data is None:
            data = {
                "islands": [],
            }
        with open(self.metadata_path, "w") as f:
            json.dump(data, f, indent=2)

    def sample(self) -> Optional[Island]:
        """Return a random island, or None if empty."""
        islands = self.get_islands()
        return random.choice(islands) if islands else None

    def get_island(self, island_id: int):
        """Returns an island instance for the given island identifier."""
        return Island(
            self.path / f"island_{island_id}", self.data, self.max_island_size
        )

    def get_size(self):
        return len(self.get_islands())

    def get_islands_budget(self):
        total = 0
        # try:
        for island in self.get_islands():
            data = island.get_n_calls_data()
            if "total" in data.keys():
                total += data["total"]
        # except:
        #     pass
        return total

    def get_budget(self):
        # data_path = self.path / "budget.json"
        # if data_path.exists():
        #     data = read_json(data_path)
        #     return data["calls"]

        return self.get_islands_budget()

    def set_budget(self, summary):
        data_path = self.path / "budget.json"
        save_json(summary, data_path)

    def is_proved(self):
        for island_store in self.get_islands():
            if island_store.is_proved():
                return True
        return False
