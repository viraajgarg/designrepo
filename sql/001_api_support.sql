BEGIN;

ALTER TABLE designs."IMAGES" DROP CONSTRAINT IF EXISTS "fk_IMAGES";
ALTER TABLE designs."IMAGES"
    ADD CONSTRAINT "fk_IMAGES_DESIGN_ID"
    FOREIGN KEY ("DESIGN_ID") REFERENCES designs."DESIGN_DETAIL" ("ID") NOT VALID;

CREATE SEQUENCE IF NOT EXISTS designs.design_detail_id_seq;
CREATE SEQUENCE IF NOT EXISTS designs.applicants_detail_id_seq;
CREATE SEQUENCE IF NOT EXISTS designs.images_id_seq;
CREATE SEQUENCE IF NOT EXISTS designs.priority_detail_id_seq;

ALTER SEQUENCE designs.design_detail_id_seq OWNED BY designs."DESIGN_DETAIL"."ID";
ALTER SEQUENCE designs.applicants_detail_id_seq OWNED BY designs."APPLICANTS_DETAIL"."ID";
ALTER SEQUENCE designs.images_id_seq OWNED BY designs."IMAGES"."ID";
ALTER SEQUENCE designs.priority_detail_id_seq OWNED BY designs."PRIORITY_DETAIL"."ID";

SELECT setval('designs.design_detail_id_seq', COALESCE(MAX("ID"), 1), MAX("ID") IS NOT NULL) FROM designs."DESIGN_DETAIL";
SELECT setval('designs.applicants_detail_id_seq', COALESCE(MAX("ID"), 1), MAX("ID") IS NOT NULL) FROM designs."APPLICANTS_DETAIL";
SELECT setval('designs.images_id_seq', COALESCE(MAX("ID"), 1), MAX("ID") IS NOT NULL) FROM designs."IMAGES";
SELECT setval('designs.priority_detail_id_seq', COALESCE(MAX("ID"), 1), MAX("ID") IS NOT NULL) FROM designs."PRIORITY_DETAIL";

ALTER TABLE designs."DESIGN_DETAIL" ALTER COLUMN "ID" SET DEFAULT nextval('designs.design_detail_id_seq');
ALTER TABLE designs."APPLICANTS_DETAIL" ALTER COLUMN "ID" SET DEFAULT nextval('designs.applicants_detail_id_seq');
ALTER TABLE designs."IMAGES" ALTER COLUMN "ID" SET DEFAULT nextval('designs.images_id_seq');
ALTER TABLE designs."PRIORITY_DETAIL" ALTER COLUMN "ID" SET DEFAULT nextval('designs.priority_detail_id_seq');

CREATE INDEX IF NOT EXISTS ix_design_detail_num_version
    ON designs."DESIGN_DETAIL" ("DESIGN_NUM_ID", "VERSION" DESC, "ID" DESC);

COMMIT;