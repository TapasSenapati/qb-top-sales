package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.Order;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {}