"""
ShopKaro Recommendation Engine Module
======================================
Provides popularity baselines, collaborative filtering (implicit feedback, ALS),
content-based filtering, hybrid recommender architectures, re-ranking logic, and
offline evaluation protocols (HitRate@K, NDCG@K, Precision@K).
"""

from shopkaro.recommendations.baselines import (
    BaselineEvalMetrics,
    BaseRecommender,
    FavouriteCategoryPopularRecommender,
    PopularOverallRecommender,
    Trending7DayRecommender,
    evaluate_recommender_at_k,
    load_test_ground_truth,
    run_day2_task1_baselines,
)
from shopkaro.recommendations.collaborative import (
    ALSHyperparameterResult,
    ImplicitALSRecommender,
    ItemToItemCFRecommender,
    run_day2_task2_collaborative_filtering,
)
from shopkaro.recommendations.hybrid import (
    ColdStartEvalSummary,
    ContentBasedRecommender,
    HybridTwoTowerRecommender,
    evaluate_cold_start_performance,
    run_day2_task3_content_and_hybrid,
)

__all__ = [
    "ALSHyperparameterResult",
    "BaseRecommender",
    "BaselineEvalMetrics",
    "ColdStartEvalSummary",
    "ContentBasedRecommender",
    "FavouriteCategoryPopularRecommender",
    "HybridTwoTowerRecommender",
    "ImplicitALSRecommender",
    "ItemToItemCFRecommender",
    "PopularOverallRecommender",
    "Trending7DayRecommender",
    "evaluate_cold_start_performance",
    "evaluate_recommender_at_k",
    "load_test_ground_truth",
    "run_day2_task1_baselines",
    "run_day2_task2_collaborative_filtering",
    "run_day2_task3_content_and_hybrid",
]
