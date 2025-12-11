package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.OrderItem;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderItemRepository extends JpaRepository<OrderItem, Long> {}

