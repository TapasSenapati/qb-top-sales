package com.tapas.qb.forecasting;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;


@EnableKafka
@SpringBootApplication
public class ForecastingServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(ForecastingServiceApplication.class, args);
    }
}
