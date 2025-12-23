package com.tapas.qb.ingestion.outbox;

import com.tapas.qb.ingestion.domain.OrderEvent;
import com.tapas.qb.ingestion.repository.OrderEventRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Component
@Slf4j
public class OutboxPublisher {

    private static final String TOPIC = "order-events";

    private final OrderEventRepository orderEventRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;

    @Value("${outbox.batch-size:100}")
    private int batchSize;

    @Value("${outbox.kafka-timeout-seconds:10}")
    private int kafkaTimeoutSeconds;

    public OutboxPublisher(OrderEventRepository orderEventRepository,
            KafkaTemplate<String, String> kafkaTemplate) {
        this.orderEventRepository = orderEventRepository;
        this.kafkaTemplate = kafkaTemplate;
    }

    @Scheduled(fixedDelay = 5000)
    @Transactional
    public void publish() {
        log.info("OutboxPublisher tick");

        // Configurable batch size with FIFO ordering (oldest first)
        var pageable = PageRequest.of(0, batchSize, Sort.by("createdAt").ascending());
        List<OrderEvent> events = orderEventRepository.findByProcessedFalse(pageable);
        log.info("Found {} unprocessed events (batch size: {})", events.size(), batchSize);

        for (OrderEvent event : events) {
            try {
                // Synchronously wait for Kafka ack with configurable timeout
                var sendResult = kafkaTemplate.send(TOPIC, event.getOrderId().toString(), event.getPayload())
                        .get(kafkaTimeoutSeconds, TimeUnit.SECONDS);

                log.info("Published event {} to Kafka partition {} offset {}",
                        event.getId(),
                        sendResult.getRecordMetadata().partition(),
                        sendResult.getRecordMetadata().offset());

                // Only mark processed AFTER Kafka confirms receipt
                event.setProcessed(true);
                event.setProcessedAt(Instant.now());
                orderEventRepository.save(event);

            } catch (Exception ex) {
                // Kafka send failed - leave event unprocessed for retry on next tick
                log.error("Failed to publish event {}, will retry", event.getId(), ex);
                // Don't mark as processed - it will be retried on next scheduled run
            }
        }
    }
}
