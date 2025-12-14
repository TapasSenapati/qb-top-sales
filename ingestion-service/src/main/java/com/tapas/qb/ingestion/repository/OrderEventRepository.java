package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.OrderEvent;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderEventRepository extends JpaRepository<OrderEvent, Long> {
    //fetch at most 100 events where processed = false, sorted by createdAt in ascending order (oldest first)
    //Conceptually, it’s similar to: SELECT * FROM ingestion.order_events WHERE processed = false ORDER BY created_at ASC LIMIT 100
    List<OrderEvent> findTop100ByProcessedFalseOrderByCreatedAtAsc();
}

