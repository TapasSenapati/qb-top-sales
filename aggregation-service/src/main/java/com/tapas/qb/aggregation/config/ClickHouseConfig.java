package com.tapas.qb.aggregation.config;

import com.clickhouse.jdbc.ClickHouseDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.Properties;

/**
 * Configuration for ClickHouse DataSource used for analytics writes.
 * Separate from PostgreSQL which handles OLTP and catalog data.
 */
@Configuration
public class ClickHouseConfig {

    private static final Logger log = LoggerFactory.getLogger(ClickHouseConfig.class);

    @Value("${clickhouse.host:clickhouse}")
    private String host;

    @Value("${clickhouse.port:8123}")
    private int port;

    @Value("${clickhouse.database:default}")
    private String database;

    @Bean
    public DataSource clickHouseDataSource() throws SQLException {
        String url = String.format("jdbc:clickhouse://%s:%d/%s", host, port, database);
        log.info("Creating ClickHouse DataSource with URL: {}", url);
        Properties properties = new Properties();
        properties.setProperty("socket_timeout", "300000");
        properties.setProperty("compress", "true");
        ClickHouseDataSource dataSource = new ClickHouseDataSource(url, properties);
        log.info("ClickHouse DataSource created successfully");
        return dataSource;
    }

    @Bean
    public JdbcTemplate clickHouseJdbcTemplate() throws SQLException {
        log.info("Creating ClickHouse JdbcTemplate");
        JdbcTemplate template = new JdbcTemplate(clickHouseDataSource());
        log.info("ClickHouse JdbcTemplate created successfully");
        return template;
    }
}
