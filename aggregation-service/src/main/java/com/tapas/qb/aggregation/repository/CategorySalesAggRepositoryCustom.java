package com.tapas.qb.aggregation.repository;

import java.util.Collection;

public interface CategorySalesAggRepositoryCustom {

    void bulkUpsert(String bucketType, Collection<UpsertData> data);
}
