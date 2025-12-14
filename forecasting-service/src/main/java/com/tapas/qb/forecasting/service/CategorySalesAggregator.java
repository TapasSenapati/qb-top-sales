package com.tapas.qb.forecasting.service;

import com.tapas.qb.forecasting.dto.OrderEventPayload;
import com.tapas.qb.forecasting.repository.CategorySalesAggRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

@Service
public class CategorySalesAggregator {

    private final CategorySalesAggRepository repository;

    public CategorySalesAggregator(CategorySalesAggRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public void aggregate(OrderEventPayload event) {

        Instant bucketStart = event.orderDate()
                .truncatedTo(ChronoUnit.DAYS);

        Instant bucketEnd = bucketStart.plus(1, ChronoUnit.DAYS);

        for (OrderEventPayload.Item item : event.items()) {
            repository.upsertDayAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    bucketStart,
                    bucketEnd,
                    item.lineAmount(),
                    (long) item.quantity()
            );
        }
    }
}
