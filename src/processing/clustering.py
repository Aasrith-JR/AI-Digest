from collections import defaultdict
from typing import Dict, List

from core.entities import Cluster


def build_clusters(
    persona: str,
    assignments: Dict[int, int],
) -> List[Cluster]:
    """
    assignments: item_id -> cluster_id
    """
    clusters: dict[int, list[int]] = defaultdict(list)

    for item_id, cluster_id in assignments.items():
        clusters[cluster_id].append(item_id)

    return [
        Cluster(
            id=cluster_id,
            persona=persona,
            representative_item_id=item_ids[0],
            item_ids=item_ids,
        )
        for cluster_id, item_ids in clusters.items()
    ]
