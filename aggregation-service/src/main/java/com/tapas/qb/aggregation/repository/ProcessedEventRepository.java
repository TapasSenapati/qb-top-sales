package com.tapas.qb.aggregation.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.Set;

public interface ProcessedEventRepository
        extends JpaRepository<ProcessedEvent, Long> {

    @Query("SELECT p.eventId FROM ProcessedEvent p WHERE p.eventId IN :eventIds")
    Set<Long> findExisting(@Param("eventIds") Collection<Long> eventIds);
}
