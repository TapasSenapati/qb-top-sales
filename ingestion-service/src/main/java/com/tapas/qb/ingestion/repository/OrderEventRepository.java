package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.OrderEvent;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderEventRepository extends JpaRepository<OrderEvent, Long> {}

