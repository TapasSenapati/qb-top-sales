package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.OrderEvent;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderEventRepository extends JpaRepository<OrderEvent, Long> {

    /**
     * Find unprocessed events sorted by creation time (oldest first).
     * Uses partial index on (created_at) WHERE processed = false for performance.
     * 
     * @param pageable configurable page size and sorting
     * @return list of unprocessed events
     */
    List<OrderEvent> findByProcessedFalse(Pageable pageable);
}
