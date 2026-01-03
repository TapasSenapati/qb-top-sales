package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.dto.TopCategoryDto;
import com.tapas.qb.aggregation.repository.TopCategoryRow;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class TopCategoryQueryService {

    private final JdbcTemplate clickHouseJdbcTemplate;
    private final JdbcTemplate postgresJdbcTemplate;

    public TopCategoryQueryService(
            @Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate,
            @Qualifier("primaryJdbcTemplate") JdbcTemplate postgresJdbcTemplate) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
        this.postgresJdbcTemplate = postgresJdbcTemplate;
    }

    public List<TopCategoryRow> topCategories(
            Long merchantId,
            String bucketType,
            Instant bucketStart,
            Instant bucketEnd,
            int limit) {

        // 1. Query ClickHouse for Top N categories by sales
        String chSql = """
                SELECT
                    category_id,
                    sum(total_sales_amount) as total_sales,
                    sum(total_units_sold) as total_units,
                    sum(order_count) as order_count
                FROM category_sales_agg
                WHERE merchant_id = ? AND bucket_type = ?
                """;

        List<Object> args = new ArrayList<>();
        args.add(merchantId);
        args.add(bucketType);

        if ("CUSTOM".equalsIgnoreCase(bucketType) && bucketEnd != null) {
            // For custom range, bucket_type matches 'DAY' usually, or we aggregate whatever
            // matches range
            // But the UI usually asks for bucket_type=DAY for ranges.
            // Let's assume bucket_type is respected from params if not "CUSTOM" or default
            // to 'DAY' if needed.
            // If the user passes "CUSTOM" as bucketType, we query DAY buckets in range.
            chSql = """
                    SELECT
                        category_id,
                        sum(total_sales_amount) as total_sales,
                        sum(total_units_sold) as total_units,
                        sum(order_count) as order_count
                    FROM category_sales_agg
                    WHERE merchant_id = ? AND bucket_type = 'DAY'
                    AND bucket_start >= fromUnixTimestamp64Milli(?)
                    AND bucket_start <= fromUnixTimestamp64Milli(?)
                    """;
            // clear args and rebuild
            args.clear();
            args.add(merchantId);
            args.add(bucketStart.toEpochMilli());
            args.add(bucketEnd.toEpochMilli());
        } else {
            // Exact match on bucket_start
            chSql += " AND bucket_start = fromUnixTimestamp64Milli(?)";
            args.add(bucketStart.toEpochMilli());
        }

        chSql += """
                GROUP BY category_id
                ORDER BY total_sales DESC
                LIMIT ?
                """;
        args.add(limit);

        List<TopCategoryDto> stats = clickHouseJdbcTemplate.query(chSql,
                (rs, rowNum) -> new TopCategoryDto(
                        rs.getLong("category_id"),
                        "Unknown", // Placeholder, will fill from Postgres
                        rs.getBigDecimal("total_sales"),
                        rs.getLong("total_units"),
                        rs.getLong("order_count")),
                args.toArray());

        if (stats.isEmpty()) {
            return List.of();
        }

        // 2. Fetch Category Names from Postgres
        var categoryIds = stats.stream().map(TopCategoryDto::categoryId).toList();

        // Dynamic IN clause
        String inSql = String.join(",", Collections.nCopies(categoryIds.size(), "?"));
        String pgSql = String.format("SELECT id, name FROM ingestion.categories WHERE id IN (%s)", inSql);

        // Uses varargs version query(sql, rse, args...)
        Map<Long, String> namesMap = postgresJdbcTemplate.query(pgSql, (rs) -> {
            var map = new HashMap<Long, String>();
            while (rs.next()) {
                map.put(rs.getLong("id"), rs.getString("name"));
            }
            return map;
        }, categoryIds.toArray());

        final Map<Long, String> names = namesMap != null ? namesMap : Collections.emptyMap();

        // 3. Merge and Return
        return stats.stream()
                .map(dto -> new TopCategoryDto(
                        dto.categoryId(),
                        names.getOrDefault(dto.categoryId(), "Unknown Category: " + dto.categoryId()),
                        dto.totalSalesAmount(),
                        dto.totalUnitsSold(),
                        dto.orderCount()))
                .map(TopCategoryRow.class::cast)
                .toList();
    }
}
