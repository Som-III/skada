import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    GroupShuffleSplit,
    GroupKFold,
    LeaveOneGroupOut,
    cross_validate,
)

from skada import SubspaceAlignmentAdapter, make_da_pipeline
from skada.metrics import PredictionEntropyScorer
from skada.model_selection import SourceTargetShuffleSplit

import pytest

# xxx(okachaiev): reconsider folders structure
# these tests should likely be moved to the folder where `model_selection`
# is implemented

@pytest.mark.parametrize(
    'cv, n_splits',
    [
        (GroupShuffleSplit(n_splits=2, test_size=0.3, random_state=0), 2),
        (GroupKFold(n_splits=2), 2),
        (LeaveOneGroupOut(), 4),
    ]
)
def test_group_based_cv(da_dataset, cv, n_splits):
    assert hasattr(cv, 'set_split_request'), 'splitter has to support routing'
    cv.set_split_request(groups='sample_domain')
    # single source, single target, target labels are masked
    X, y, sample_domain = da_dataset.pack_for_train(as_sources=['s', 's2'], as_targets=['t', 't2'])
    # by default, each estimator in the pipeline is wrapped into `Shared` selector
    pipe = make_da_pipeline(
        SubspaceAlignmentAdapter(n_components=2),
        LogisticRegression(),
    )
    pipe.fit(X, y, sample_domain=sample_domain)
    scores = cross_validate(
        pipe,
        X,
        y,
        cv=cv,
        params={'sample_domain': sample_domain},
        scoring=PredictionEntropyScorer(),
    )['test_score']
    assert scores.shape[0] == n_splits, "evaluate all splits"
    # xxx(okachaiev): make sure we understand why/when validation fails
    # (some results are certainly None in here)
    assert np.any(~np.isnan(scores)), "at least some scores are computed"


def test_domain_aware_split(da_dataset):
    X, y, sample_domain = da_dataset.pack_for_train(as_sources=['s', 's2'], as_targets=['t', 't2'])
    # by default, each estimator in the pipeline is wrapped into `Shared` selector
    pipe = make_da_pipeline(
        SubspaceAlignmentAdapter(n_components=2),
        LogisticRegression(),
    )
    pipe.fit(X, y, sample_domain=sample_domain)
    n_splits = 4
    cv = SourceTargetShuffleSplit(n_splits=n_splits, test_size=0.3, random_state=0)
    scores = cross_validate(
        pipe,
        X,
        y,
        cv=cv,
        params={'sample_domain': sample_domain},
        scoring=PredictionEntropyScorer(),
    )['test_score']
    assert scores.shape[0] == n_splits, "evaluate all splits"
    assert np.all(~np.isnan(scores)), "at least some scores are computed"
