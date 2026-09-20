package com.eidss.gateway.audit;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Persistence gateway for {@link AdvisoryAuditRecord}, deliberately hand-written against
 * {@link EntityManager} instead of a Spring Data {@code JpaRepository}/{@code CrudRepository}.
 *
 * <p>Spring Data's CRUD repositories give you {@code delete}/{@code deleteById}/{@code save}
 * (which is really upsert) for free — exactly the operations an append-only audit trail must
 * not expose. By writing this class ourselves we guarantee, at the type level, that
 * <b>no update or delete method exists anywhere in this codebase</b> for audit records: only
 * {@link #append(AdvisoryAuditRecord)} (always an INSERT, via {@code persist}) and read-only
 * queries are defined below.
 */
@Repository
public class AdvisoryAuditRecordStore {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional
    public void append(AdvisoryAuditRecord record) {
        entityManager.persist(record);
    }

    @Transactional(readOnly = true)
    public List<AdvisoryAuditRecord> findRecent(int limit) {
        return entityManager.createQuery(
                        "select r from AdvisoryAuditRecord r order by r.id desc", AdvisoryAuditRecord.class)
                .setMaxResults(Math.max(limit, 0))
                .getResultList();
    }

    @Transactional(readOnly = true)
    public List<AdvisoryAuditRecord> findAllOrderedById() {
        return entityManager.createQuery(
                        "select r from AdvisoryAuditRecord r order by r.id asc", AdvisoryAuditRecord.class)
                .getResultList();
    }

    @Transactional(readOnly = true)
    public long count() {
        return entityManager.createQuery("select count(r) from AdvisoryAuditRecord r", Long.class)
                .getSingleResult();
    }
}
