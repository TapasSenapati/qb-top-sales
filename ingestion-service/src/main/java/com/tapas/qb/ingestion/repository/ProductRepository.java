package com.tapas.qb.ingestion.repository;

import com.tapas.qb.ingestion.domain.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductRepository extends JpaRepository<Product, Long> {

    @Query("select p.categoryId from Product p where p.id = :productId")
    Long findCategoryIdByProductId(@Param("productId") Long productId);
}
