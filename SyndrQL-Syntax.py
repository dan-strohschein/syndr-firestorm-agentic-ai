#
# SELECT DOCUMENTS FROM "Authors" Join "Books" On "Authors"."DocumentID" == "Books"."AuthorsID" Where "Authors"."DocumentID" == "186ed63c0ae87940_10c" WITH RELATIONSHIP "Books";
# UPDATE DOCUMENTS IN BUNDLE "Authors" ("AuthorName" = "Dan Strohschein-669" ) WHERE "DocumentID" == "187320fc9a770e28_33";
# DELETE DOCUMENTS FROM "Books" WHERE "DocumentID" == "18712e2dbd27c5e8_2a";
# SELECT DOCUMENTS FROM "Authors" WHERE "AuthorName" == "Dan Strohschein-123" ;
# SELECT DOCUMENTS FROM "Authors" WHERE "Age" > 15 ORDER BY "AuthorName" DESC ;
# SELECT TOP 5 * FROM "Authors";
# SELECT COUNT(*) FROM "Books" WHERE "PublishedYear" >= 2010 ;
# SELECT * FROM "Books" WHERE "Age" > 5 GROUP BY "PublishedYear" ;
# SELECT "Authors"."AuthorName", "Books"."Title" FROM "Authors" Join "Books" On "Authors"."DocumentID" == "Books"."AuthorsID" WHERE "Authors"."Age" > 30 AND "Books"."PublishedYear" >= 2015 ORDER BY "Books"."Title" ASC ;
# SELECT "Title" FROM "books";
#
#
#
#
#
#