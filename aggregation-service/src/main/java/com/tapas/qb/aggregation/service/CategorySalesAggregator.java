package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.dto.OrderEventPayload;
import com.tapas.qb.aggregation.repository.CategorySalesAggRepository;
import com.tapas.qb.aggregation.repository.ProcessedEvent;
import com.tapas.qb.aggregation.repository.ProcessedEventRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;

@Service
public class CategorySalesAggregator {
    private final CategorySalesAggRepository aggRepo;
    private final ProcessedEventRepository processedRepo;

    public CategorySalesAggregator(CategorySalesAggRepository aggRepo, ProcessedEventRepository processedRepo) {
        this.aggRepo = aggRepo;
        this.processedRepo = processedRepo;
    }

    @Transactional
    public void aggregate(OrderEventPayload event) {

        // Try to claim the event
        if (processedRepo.existsById(event.eventId())) {
            return; // already processed → no-op
        }
        processedRepo.save(
                new ProcessedEvent(event.eventId(), Instant.now())
        );

        Instant dayStart = event.orderDate()
                .truncatedTo(ChronoUnit.DAYS);
        Instant dayEnd = dayStart.plus(1, ChronoUnit.DAYS);

        Instant weekStart = weekBucketStart(event.orderDate());
        Instant weekEnd = weekStart.plus(7, ChronoUnit.DAYS);

        Instant monthStart = monthBucketStart(event.orderDate());
        Instant monthEnd = monthStart
                .atZone(ZoneOffset.UTC)
                .plusMonths(1)
                .toInstant();

        for (OrderEventPayload.Item item : event.items()) {
            aggRepo.upsertDayAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    dayStart,
                    dayEnd,
                    item.lineAmount(),
                    (long) item.quantity()
            );
            aggRepo.upsertWeekAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    weekStart,
                    weekEnd,
                    item.lineAmount(),
                    (long) item.quantity()
            );
            aggRepo.upsertMonthAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    monthStart,
                    monthEnd,
                    item.lineAmount(),
                    (long) item.quantity()
            );
        }
    }

    private static Instant weekBucketStart(Instant orderDate) {
        ZonedDateTime zdt = orderDate.atZone(ZoneOffset.UTC);

        ZonedDateTime weekStart = zdt
                .with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
                .truncatedTo(ChronoUnit.DAYS);

        return weekStart.toInstant();
    }

    private static Instant monthBucketStart(Instant orderDate) {
        ZonedDateTime zdt = orderDate.atZone(ZoneOffset.UTC);

        ZonedDateTime monthStart = zdt
                .withDayOfMonth(1)
                .truncatedTo(ChronoUnit.DAYS);

        return monthStart.toInstant();
    }

}
