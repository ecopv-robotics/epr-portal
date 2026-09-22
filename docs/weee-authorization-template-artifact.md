# Germany WEEE Authorization Template Contract

## Reference

- Source: `2-德国weee授权书模板 非德国公司.docx`
- Embedded application asset: `backend/app/assets/germany_weee_authorization_non_german.docx`
- SHA-256: `A961DAF6B90FD021474120EE5D98FBB91A4DD34F4C6767E62F6838A5506B6E2C`
- Pages: 2
- Sections: 1
- Page: A4 portrait, 0.98 inch left/right/top margins, 0.79 inch bottom margin
- Primary typeface: Arial

## Preserved Content

- German title and all six agreement clauses.
- ECOPV-EU GmbH representative details in the second table.
- Page geometry, paragraph spacing, tables, signature lines and German labels.

## Editable Slot Map

| Location | Value |
| --- | --- |
| First table row 1 value | Customer company English name |
| First table row 2 value | Customer English registered address |
| First table row 3 value | Postal code and English city |
| First table row 4 value | Contact phone |
| First table row 5 value | Contact email |
| First table row 6 value | Legal representative English or pinyin name |
| First table row 7 value | Registration number or unified social credit code |
| Customer place and date line | English city and generation date |
| Customer signature area | Uploaded legal representative signature and CEO role |
| Customer company label | Customer company English name |

## Removal Rules

- Red Chinese helper text is instructional content and must not appear in generated authorization documents.
- No agreement clause or representative-party value may be rewritten from customer input.

## Fidelity Gates

- Generated files remain two A4 portrait pages.
- Both tables retain seven rows and their original column widths and borders.
- No red helper text remains.
- The customer signature and company name stay within the right-hand signature block.
