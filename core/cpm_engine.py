"""
Motor de Ruta Crítica (CPM) para el cronograma Kratos FSAE.
Implementa forward pass, backward pass, cálculo de holgura y detección de ruta crítica.
"""
import pandas as pd
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class CPMNode:
    id: str
    duration: float = 0.0
    predecessors: list = field(default_factory=list)
    successors: list = field(default_factory=list)
    # Forward pass
    early_start: float = 0.0
    early_finish: float = 0.0
    # Backward pass
    late_start: float = float("inf")
    late_finish: float = float("inf")
    # Slack
    total_float: float = 0.0
    free_float: float = 0.0
    is_critical: bool = False
    # Metadata
    subsistema: str = ""
    microsubsistema: str = ""
    actividad: str = ""


class CPMEngine:
    """
    Motor CPM completo con soporte para:
    - Forward/backward pass
    - Detección de ruta crítica
    - Holgura total y libre
    - Filtrado por subsistema/microsubsistema
    - Detección de ciclos
    """

    def __init__(self):
        self.nodes: dict[str, CPMNode] = {}
        self.critical_path: list[str] = []
        self.project_duration: float = 0.0
        self._computed = False

    def load_from_dataframe(self, df: pd.DataFrame):
        """Carga actividades desde el DataFrame limpio."""
        self.nodes.clear()
        self._computed = False

        for _, row in df.iterrows():
            node_id = str(row["id"])
            duration = row.get("duracion_dias", 0)
            if pd.isna(duration) or duration <= 0:
                duration = 1  # Mínimo 1 día para evitar nodos colapsados

            preds_raw = row.get("predecesores", [])
            if not isinstance(preds_raw, list):
                preds_raw = []
            # Filtrar predecesores no resueltos (empiezan con ?)
            preds = [p for p in preds_raw if not str(p).startswith("?")]

            node = CPMNode(
                id=node_id,
                duration=float(duration),
                predecessors=preds,
                subsistema=str(row.get("subsistema", "")),
                microsubsistema=str(row.get("microsubsistema", "")),
                actividad=str(row.get("actividad", "")),
            )
            self.nodes[node_id] = node

        # Construir lista de sucesores y validar predecesores
        for node_id, node in self.nodes.items():
            valid_preds = []
            for pred_id in node.predecessors:
                if pred_id in self.nodes:
                    self.nodes[pred_id].successors.append(node_id)
                    valid_preds.append(pred_id)
            node.predecessors = valid_preds

    def _break_cycles(self) -> list[tuple[str, str]]:
        """
        Detecta y rompe ciclos en el grafo usando DFS.
        Estrategia: remove back-edges (la arista que cierra el ciclo).
        Retorna lista de aristas removidas [(from, to), ...].
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self.nodes}
        broken_edges = []

        def dfs(nid):
            color[nid] = GRAY
            for succ in list(self.nodes[nid].successors):
                if succ not in color:
                    continue
                if color[succ] == GRAY:
                    # Back-edge found → break it
                    self.nodes[nid].successors.remove(succ)
                    if nid in self.nodes[succ].predecessors:
                        self.nodes[succ].predecessors.remove(nid)
                    broken_edges.append((nid, succ))
                elif color[succ] == WHITE:
                    dfs(succ)
            color[nid] = BLACK

        for nid in self.nodes:
            if color[nid] == WHITE:
                dfs(nid)

        return broken_edges

    def _topological_sort(self) -> list[str]:
        """Ordenamiento topológico usando Kahn's algorithm."""
        in_degree = defaultdict(int)
        for nid in self.nodes:
            in_degree[nid] = len(self.nodes[nid].predecessors)

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for succ in self.nodes[nid].successors:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        # Si quedan nodos sin procesar (ciclos residuales o desconectados),
        # agregarlos al final para que CPM no los ignore
        remaining = [nid for nid in self.nodes if nid not in order]
        order.extend(remaining)

        return order

    def compute(self) -> dict:
        """
        Ejecuta el cálculo CPM completo.
        Rompe ciclos automáticamente y calcula sobre el grafo acíclico resultante.
        Retorna un dict con estadísticas del cálculo.
        """
        if not self.nodes:
            return {"error": "No hay actividades cargadas"}

        # Romper ciclos
        broken = self._break_cycles()

        # Topological sort
        topo_order = self._topological_sort()

        # ── Forward Pass ──
        for nid in topo_order:
            node = self.nodes[nid]
            if not node.predecessors:
                node.early_start = 0
            else:
                valid_preds = [pid for pid in node.predecessors if pid in self.nodes]
                if valid_preds:
                    node.early_start = max(
                        self.nodes[pid].early_finish for pid in valid_preds
                    )
                else:
                    node.early_start = 0
            node.early_finish = node.early_start + node.duration

        # Duración del proyecto
        self.project_duration = max(
            node.early_finish for node in self.nodes.values()
        ) if self.nodes else 0

        # ── Backward Pass ──
        for nid in reversed(topo_order):
            node = self.nodes[nid]
            valid_succs = [sid for sid in node.successors if sid in self.nodes]
            if not valid_succs:
                node.late_finish = self.project_duration
            else:
                node.late_finish = min(
                    self.nodes[sid].late_start for sid in valid_succs
                )
            node.late_start = node.late_finish - node.duration

        # ── Calcular holguras ──
        for nid, node in self.nodes.items():
            node.total_float = node.late_start - node.early_start
            valid_succs = [sid for sid in node.successors if sid in self.nodes]
            if valid_succs:
                min_succ_es = min(
                    self.nodes[sid].early_start for sid in valid_succs
                )
                node.free_float = min_succ_es - node.early_finish
            else:
                node.free_float = self.project_duration - node.early_finish

            node.is_critical = abs(node.total_float) < 0.5  # 0.5 día tolerancia

        # ── Extraer ruta crítica ──
        self.critical_path = [
            nid for nid, node in self.nodes.items()
            if node.is_critical
        ]
        self.critical_path.sort(key=lambda x: self.nodes[x].early_start)

        self._computed = True

        return {
            "project_duration_days": self.project_duration,
            "total_activities": len(self.nodes),
            "critical_activities": len(self.critical_path),
            "cycles_broken": len(broken),
            "broken_edges": broken[:10],  # Primeras 10 para no saturar
            "activities_with_predecessors": sum(
                1 for n in self.nodes.values() if n.predecessors
            ),
            "start_nodes": sum(
                1 for n in self.nodes.values() if not n.predecessors
            ),
            "end_nodes": sum(
                1 for n in self.nodes.values() if not n.successors
            ),
        }

    def get_critical_path_df(self) -> pd.DataFrame:
        """Retorna la ruta crítica como DataFrame."""
        if not self._computed:
            self.compute()

        rows = []
        for nid in self.critical_path:
            node = self.nodes[nid]
            rows.append({
                "ID": node.id,
                "Actividad": node.actividad,
                "Subsistema": node.subsistema,
                "Microsubsistema": node.microsubsistema,
                "Duración": node.duration,
                "ES": node.early_start,
                "EF": node.early_finish,
                "LS": node.late_start,
                "LF": node.late_finish,
                "Holgura": node.total_float,
            })
        return pd.DataFrame(rows)

    def get_full_schedule_df(self) -> pd.DataFrame:
        """Retorna el cronograma completo con cálculos CPM."""
        if not self._computed:
            self.compute()

        rows = []
        for nid, node in self.nodes.items():
            rows.append({
                "ID": node.id,
                "Actividad": node.actividad,
                "Subsistema": node.subsistema,
                "Microsubsistema": node.microsubsistema,
                "Duración": node.duration,
                "ES": node.early_start,
                "EF": node.early_finish,
                "LS": node.late_start,
                "LF": node.late_finish,
                "Holgura Total": node.total_float,
                "Holgura Libre": node.free_float,
                "Es Crítica": node.is_critical,
                "Predecesores": ", ".join(node.predecessors),
                "Sucesores": ", ".join(node.successors),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("ES").reset_index(drop=True)
        return df

    def get_critical_path_by_subsystem(self, subsistema: str) -> list[str]:
        """Filtra ruta crítica por subsistema."""
        return [
            nid for nid in self.critical_path
            if self.nodes[nid].subsistema == subsistema
        ]

    def get_critical_path_by_micro(self, microsubsistema: str) -> list[str]:
        """Filtra ruta crítica por microsubsistema."""
        return [
            nid for nid in self.critical_path
            if self.nodes[nid].microsubsistema == microsubsistema
        ]

    def get_stats_by_subsystem(self) -> dict:
        """Estadísticas CPM agrupadas por subsistema."""
        stats = defaultdict(lambda: {
            "total": 0, "critical": 0, "avg_float": 0, "max_duration": 0
        })
        for node in self.nodes.values():
            sub = node.subsistema or "Sin asignar"
            stats[sub]["total"] += 1
            if node.is_critical:
                stats[sub]["critical"] += 1
            stats[sub]["avg_float"] += node.total_float
            stats[sub]["max_duration"] = max(stats[sub]["max_duration"], node.duration)

        for sub in stats:
            if stats[sub]["total"] > 0:
                stats[sub]["avg_float"] /= stats[sub]["total"]
                stats[sub]["avg_float"] = round(stats[sub]["avg_float"], 1)

        return dict(stats)
