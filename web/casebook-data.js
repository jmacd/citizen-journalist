window.MENDO_CASEBOOK_DATA = {
  "generatedAt": "2026-08-22T16:08:57.430Z",
  "schema_version": 1,
  "case": {
    "id": "UM_2025-0004",
    "title": "MUSD Water System Reconstruction - Stream Restoration Modification",
    "agency": "Mendocino County Planning and Building Services",
    "applicant": "Mendocino Unified School District",
    "status": "continued",
    "current_hearing": "2026-08-20",
    "next_hearing": "2026-09-03",
    "description": "Coastal development use-permit modification adding restoration of an unnamed tributary to Slaughterhouse Gulch to MUSD's previously approved Water System Reconstruction Project.",
    "locations": {
      "project_site": {
        "address": "44020 Little Lake Road, Mendocino, CA 95460",
        "note": "County and Coastal Commission records also use 44100 Little Lake Road."
      },
      "applicant_contact": {
        "address": "44141 Little Lake Road, Mendocino, CA 95460",
        "note": "Mailing/contact address; do not treat as the construction site."
      },
      "apns": [
        "119-100-03",
        "119-100-04",
        "119-100-23"
      ],
      "coordinates": {
        "latitude": 39.31265,
        "longitude": -123.78289
      }
    }
  },
  "relationships": {
    "direct_lineage": [
      {
        "id": "SCH_2020080439",
        "type": "ceqa_record",
        "relationship": "environmental_record",
        "began": 2020,
        "source_ids": [
          "ceqanet_original_mnd",
          "ceqanet_original_nod",
          "ceqanet_subsequent_mnd",
          "ceqanet_final_subsequent_mnd",
          "ceqanet_musd_2023_nod",
          "ceqanet_county_2024_nod",
          "ceqanet_2024_addendum_nod",
          "ceqanet_water_supply_amendment",
          "ceqanet_2026_addendum",
          "ceqanet_cdfw_nod",
          "ceqanet_2026_revised_addendum"
        ]
      },
      {
        "id": "U_2023-0004",
        "type": "county_use_permit",
        "relationship": "original_county_permit",
        "decision_date": "2024-04-04",
        "decision": "approved_with_conditions",
        "source_ids": [
          "ceqanet_county_2024_nod",
          "ccc_appeal_report"
        ]
      },
      {
        "id": "A-1-MEN-24-0017",
        "type": "coastal_commission_appeal",
        "relationship": "appeal_of_U_2023-0004",
        "filed": "2024-04-22",
        "source_ids": [
          "ccc_appeal_report"
        ]
      },
      {
        "id": "UM_2024-0008",
        "type": "county_permit_modification",
        "relationship": "predecessor_modification",
        "decision_date": "2024-12-19",
        "decision": "approved_with_conditions",
        "source_ids": [
          "ceqanet_2024_addendum_nod",
          "hearing_video_2024_12_05",
          "hearing_video_2024_12_19",
          "county_2024_conditions_memo",
          "county_2024_resolution_redline",
          "county_pc_2024_0019",
          "county_exhibit_i",
          "ccc_appeal_report"
        ]
      },
      {
        "id": "PC_2024-0019",
        "type": "county_resolution",
        "relationship": "approval_of_UM_2024-0008",
        "effect": "superseded_U_2023-0004",
        "source_ids": [
          "county_pc_2024_0019",
          "ccc_appeal_report"
        ]
      },
      {
        "id": "A-1-MEN-25-0002",
        "type": "coastal_commission_appeal",
        "relationship": "appeal_of_UM_2024-0008",
        "filed": "2025-01-17",
        "source_ids": [
          "ccc_appeal_report"
        ]
      },
      {
        "id": "UM_2025-0004",
        "type": "county_permit_modification",
        "relationship": "current_case",
        "hearing_date": "2026-08-20",
        "decision": "continued",
        "source_ids": [
          "county_2026_agenda",
          "county_2026_staff_report",
          "county_mnd",
          "county_2026_addendum",
          "county_draft_resolution",
          "county_revised_resolution",
          "hearing_video_2026_08_20"
        ]
      },
      {
        "id": "EPIMS-MEN-66299-R1C",
        "type": "cdfw_streambed_alteration_agreement",
        "relationship": "stream_restoration_authorization",
        "approved": "2026-06-08",
        "source_ids": [
          "ceqanet_cdfw_nod"
        ]
      },
      {
        "id": "WDID_1B26057WNME",
        "type": "regional_water_board_record",
        "relationship": "stream_restoration_authorization",
        "issued": "2026-05-28",
        "source_ids": [
          "rwqcb_noa"
        ]
      }
    ],
    "related_not_direct": [
      {
        "id": "SCH_2022020568",
        "type": "ceqa_record",
        "relationship": "separate_recycled_water_project"
      },
      {
        "id": "U_2022-0012",
        "type": "county_use_permit",
        "relationship": "separate_recycled_water_project",
        "decision_date": "2023-07-06"
      }
    ],
    "excluded_false_matches": [
      {
        "id": "U_2020-0010",
        "reason": "Separate MUSD high-school modernization permit; not a predecessor of the Water System Reconstruction Project."
      }
    ]
  },
  "events": [
    {
      "date": "2022-08-29",
      "event": "MCCSD approved a draft potable Water Supply and Storage Project MOU with MUSD by a 5-0 vote.",
      "source_ids": [
        "mccsd_2022_08_29_board_minutes"
      ]
    },
    {
      "date": "2022-09-08",
      "event": "MUSD approved the first potable Water Supply and Storage Project MOU by a 5-0 vote.",
      "source_ids": [
        "musd_2022_09_08_board_minutes",
        "musd_2022_09_08_board_packet"
      ]
    },
    {
      "date": "2022-10-03",
      "event": "MCCSD rescinded its draft approval and approved the final 2022 MOU by separate 5-0 votes.",
      "source_ids": [
        "mccsd_2022_10_03_board_minutes"
      ]
    },
    {
      "date": "2023-04-19",
      "event": "MCCSD approved the updated 2023 potable-project MOU by a 4-0 vote with one director absent.",
      "source_ids": [
        "mccsd_2023_04_19_board_minutes",
        "mccsd_2023_04_19_board_packet"
      ]
    },
    {
      "date": "2023-04-20",
      "event": "MUSD approved the updated potable-project MOU by a 4-0-1 vote; the signed instrument is dated April 20.",
      "source_ids": [
        "musd_2023_04_20_board_minutes",
        "musd_2023_04_20_board_packet",
        "mccsd_musd_2023_mou"
      ]
    },
    {
      "date": "2024-11-21",
      "event": "MUSD voted 3-0 to rescind the April 2023 MOU and adopt the revised potable-project MOU.",
      "source_ids": [
        "musd_2024_11_21_board_minutes",
        "musd_2024_11_21_board_packet"
      ]
    },
    {
      "date": "2024-11-25",
      "event": "MCCSD rescinded the April 20, 2023 MOU and adopted a revised potable Water Supply and Storage Project MOU by separate 4-0 votes.",
      "source_ids": [
        "mccsd_2024_11_25_board_minutes",
        "mccsd_2024_11_25_board_packet",
        "mccsd_musd_2024_mou"
      ]
    },
    {
      "date": "2020-08-26",
      "event": "Original MND review began under SCH 2020080439.",
      "source_ids": [
        "ceqanet_original_mnd"
      ]
    },
    {
      "date": "2020-10-15",
      "event": "MUSD adopted the original MND and approved the project.",
      "source_ids": [
        "ceqanet_original_nod"
      ]
    },
    {
      "date": "2023-05-11",
      "event": "Subsequent MND review began for the expanded project.",
      "source_ids": [
        "ceqanet_subsequent_mnd"
      ]
    },
    {
      "date": "2023-06-28",
      "event": "MUSD approved the modified project and Subsequent MND.",
      "source_ids": [
        "ceqanet_musd_2023_nod",
        "ceqanet_final_subsequent_mnd"
      ]
    },
    {
      "date": "2024-04-04",
      "event": "County conditionally approved U_2023-0004.",
      "source_ids": [
        "ceqanet_county_2024_nod",
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2024-04-22",
      "event": "Coastal Commission appeal A-1-MEN-24-0017 was filed.",
      "source_ids": [
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2024-12-09",
      "event": "MUSD filed a Notice of Determination for the 2024 project Addendum.",
      "source_ids": [
        "ceqanet_2024_addendum_nod"
      ]
    },
    {
      "date": "2024-12-05",
      "event": "UM_2024-0008 hearing continued for revised conditions.",
      "source_ids": [
        "hearing_video_2024_12_05",
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2024-12-19",
      "event": "County approved UM_2024-0008 and adopted PC 2024-0019.",
      "source_ids": [
        "hearing_video_2024_12_19",
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2025-01-17",
      "event": "Coastal Commission appeal A-1-MEN-25-0002 was filed.",
      "source_ids": [
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2025-04-09",
      "event": "Coastal Commission found no substantial issue on both appeals.",
      "source_ids": [
        "ccc_appeal_report"
      ]
    },
    {
      "date": "2025-12-01",
      "event": "State Water Board approval of a water-supply permit amendment was posted.",
      "source_ids": [
        "ceqanet_water_supply_amendment"
      ]
    },
    {
      "date": "2026-05-28",
      "event": "Regional Water Board authorized the stream-restoration work.",
      "source_ids": [
        "rwqcb_noa"
      ]
    },
    {
      "date": "2026-06-08",
      "event": "CDFW executed the Streambed Alteration Agreement.",
      "source_ids": [
        "ceqanet_cdfw_nod"
      ]
    },
    {
      "date": "2026-08-20",
      "event": "Planning Commission unanimously continued UM_2025-0004 to September 3, 2026.",
      "source_ids": [
        "county_2026_agenda",
        "county_2026_staff_report",
        "hearing_video_2026_08_20"
      ]
    }
  ],
  "meeting_cycles": [
    {
      "id": "environmental_baseline_2020",
      "dates": "August-October 2020",
      "title": "Original environmental review and MUSD approval",
      "forum": "Mendocino Unified School District",
      "identifiers": [
        "SCH_2020080439"
      ],
      "summary": "The original MND established the environmental baseline for replacement tanks, wells, treatment facilities, access, and security work.",
      "event_dates": [
        "2020-08-26",
        "2020-10-15"
      ],
      "source_ids": [
        "ceqanet_original_mnd",
        "ceqanet_original_nod"
      ]
    },
    {
      "id": "expanded_project_2023",
      "dates": "May-July 2023",
      "title": "Expanded project and Subsequent MND",
      "forum": "Mendocino Unified School District",
      "identifiers": [
        "SCH_2020080439"
      ],
      "summary": "MUSD evaluated and approved a substantially expanded water-system design through a Subsequent MND.",
      "event_dates": [
        "2023-05-11",
        "2023-06-28"
      ],
      "source_ids": [
        "ceqanet_subsequent_mnd",
        "ceqanet_final_subsequent_mnd",
        "ceqanet_musd_2023_nod"
      ]
    },
    {
      "id": "original_county_permit_2024",
      "dates": "April 2024-April 2025",
      "title": "Original County permit and first Coastal Commission appeal",
      "forum": "County Planning Commission / California Coastal Commission",
      "identifiers": [
        "U_2023-0004",
        "A-1-MEN-24-0017"
      ],
      "summary": "The County conditionally approved the original coastal use permit. Max Yeh appealed it to the Coastal Commission; that appeal was ultimately considered with the later modification appeal.",
      "event_dates": [
        "2024-04-04",
        "2024-04-22",
        "2025-04-09"
      ],
      "source_ids": [
        "ceqanet_county_2024_nod",
        "ccc_appeal_report"
      ]
    },
    {
      "id": "first_modification_2024",
      "dates": "December 2024-April 2025",
      "title": "First modification, continued hearing, and second appeal",
      "forum": "County Planning Commission / California Coastal Commission",
      "identifiers": [
        "UM_2024-0008",
        "PC_2024-0019",
        "A-1-MEN-25-0002"
      ],
      "summary": "The December 5 hearing was continued for revised conditions. The County approved the modification December 19; a second Coastal Commission appeal followed. The Commission found no substantial issue on both appeals.",
      "event_dates": [
        "2024-12-05",
        "2024-12-09",
        "2024-12-19",
        "2025-01-17",
        "2025-04-09"
      ],
      "source_ids": [
        "ceqanet_2024_addendum_nod",
        "hearing_video_2024_12_05",
        "hearing_video_2024_12_19",
        "county_2024_conditions_memo",
        "county_2024_resolution_redline",
        "county_pc_2024_0019",
        "county_exhibit_i",
        "ccc_appeal_report"
      ]
    },
    {
      "id": "stream_restoration_2026",
      "dates": "May-August 2026",
      "title": "Stream-restoration modification and August 20 hearing",
      "forum": "Resource agencies / County Planning Commission",
      "identifiers": [
        "UM_2025-0004",
        "EPIMS-MEN-66299-R1C",
        "WDID_1B26057WNME"
      ],
      "summary": "CDFW and the Regional Water Board authorized the restoration component. The County assembled a new modification packet, agency responses, revised resolution, and public comments for August 20. After discussing several conditions, the Commission unanimously continued the item to September 3.",
      "event_dates": [
        "2026-05-28",
        "2026-06-08",
        "2026-08-20"
      ],
      "source_ids": [
        "county_2026_agenda",
        "county_2026_staff_report",
        "county_2026_addendum",
        "county_hydro_study",
        "county_drainage_channel",
        "county_maps",
        "county_draft_resolution",
        "county_project_plans",
        "county_ccc_comments",
        "county_cdfw_comments",
        "county_rwqcb_comments",
        "county_staff_response",
        "county_biological_evaluation",
        "county_revised_resolution",
        "rwqcb_noa",
        "ceqanet_2026_addendum",
        "ceqanet_cdfw_nod",
        "ceqanet_2026_revised_addendum",
        "hearing_video_2026_08_20",
        "public_comment_maeder",
        "public_comment_orourke",
        "public_comment_yeh_1",
        "public_comment_aranguren",
        "public_request_renotice",
        "public_comment_yeh_2",
        "public_comment_jung",
        "public_comment_orourke_2",
        "public_comment_stavely",
        "public_comment_yeh_3",
        "public_comment_walton"
      ]
    }
  ],
  "sources": [
    {
      "id": "county_2026_agenda",
      "title": "Planning Commission Agenda - August 20, 2026",
      "publisher": "Mendocino County",
      "document_id": 79018,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79018/639217056508670000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_2026_staff_report",
      "title": "UM_2025-0004 Staff Report",
      "publisher": "Mendocino County",
      "document_id": 79030,
      "published_at": "2026-08-10T11:18:44.020Z",
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79030/639219575240200000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_mnd",
      "title": "Initial Study/Mitigated Negative Declaration SCH 2020080439",
      "publisher": "Mendocino County",
      "document_id": 68353,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/68353/638677968466930000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2024-12-05",
      "note": "Reused in the 2026 packet; not a new 2026 MND."
    },
    {
      "id": "county_2026_addendum",
      "title": "Addendum to MND",
      "publisher": "Mendocino County",
      "document_id": 79036,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79036/639219585076100000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20",
      "note": "Identity with CEQAnet document 15 has not been established."
    },
    {
      "id": "county_hydro_study",
      "title": "Hydro Study",
      "publisher": "Mendocino County",
      "document_id": 79040,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79040/639219586045500000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_drainage_channel",
      "title": "Drainage Channel",
      "publisher": "Mendocino County",
      "document_id": 79042,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79042/639219586235770000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_maps",
      "title": "Maps",
      "publisher": "Mendocino County",
      "document_id": 79044,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79044/639219586788670000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_draft_resolution",
      "title": "Draft Resolution",
      "publisher": "Mendocino County",
      "document_id": 79046,
      "published_at": "2026-08-10T11:38:20.623Z",
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79046/639219587006230000",
      "attachment_url": "https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=AMT%3A2608070123180891&ActivityNo=UM_2025-0004",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/conditions/2026-08-initial-draft-resolution.pdf",
      "native_path": "captures/cases/UM_2025-0004/conditions/2026-08-initial-draft-resolution.docx",
      "bytes": 139642,
      "sha256": "cae55b6a6263aa8fa527a0f5099db1e4d1a81a95adebf4db38f7156f0b70d8e8",
      "first_seen_hearing": "2026-08-20",
      "version_of": "UM_2025-0004_resolution",
      "version": "initial",
      "condition_count": 19,
      "note": "Directly retrieved from the anonymous eTRAKiT attachment endpoint. The matching native DOCX has SHA-256 1c0d8572bd8698785401c57b5520f556b8008e7803b94ac8dcd94905041c0ac0."
    },
    {
      "id": "county_project_plans",
      "title": "Project Plans",
      "publisher": "Mendocino County",
      "document_id": 79132,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79132/639222353428900000",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_revised_resolution",
      "title": "Revised Resolution",
      "publisher": "Mendocino County",
      "document_id": 79272,
      "published_at": "2026-08-18T08:42:20.758Z",
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79272/639226393407582655",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20",
      "version_of": "UM_2025-0004_resolution",
      "version": "revised_draft",
      "condition_count_status": "strong_inference_20_direct_inspection_needed"
    },
    {
      "id": "county_ccc_comments",
      "title": "California Coastal Commission Comments",
      "publisher": "Mendocino County",
      "document_id": 79256,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79256",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_cdfw_comments",
      "title": "California Department of Fish and Wildlife Comments",
      "publisher": "Mendocino County",
      "document_id": 79264,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79264",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_rwqcb_comments",
      "title": "Regional Water Quality Control Board Comments",
      "publisher": "Mendocino County",
      "document_id": 79266,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79266",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_staff_response",
      "title": "Staff Response to Coastal Commission Comments",
      "publisher": "Mendocino County",
      "document_id": 79268,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79268/639226392582380105",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "county_biological_evaluation",
      "title": "Biological Evaluation",
      "publisher": "Mendocino County",
      "document_id": 79270,
      "document_date": "2026-03-05",
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79270/639226393021135487",
      "status": "identified_unretrieved",
      "first_seen_hearing": "2026-08-20"
    },
    {
      "id": "ccc_appeal_report",
      "title": "Appeal Substantial Issue Determination A-1-MEN-24-0017 and A-1-MEN-25-0002",
      "publisher": "California Coastal Commission",
      "document_date": "2025-04-09",
      "url": "https://documents.coastal.ca.gov/reports/2025/4/W12a-W12b/W12a-W12b-4-2025-report.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/W12a-W12b-4-2025-report.pdf",
      "bytes": 368692,
      "sha256": "ee08ff83e06614780f370a90eaee25b90798c3dd156264563a542a39679e2fc6"
    },
    {
      "id": "ceqanet_original_mnd",
      "title": "Original Mitigated Negative Declaration",
      "publisher": "California State Clearinghouse",
      "document_date": "2020-08-26",
      "url": "https://ceqanet.lci.ca.gov/2020080439/2",
      "status": "captured",
      "attachment_url": "https://ceqanet.lci.ca.gov/2020080439/2/Attachment/CS-0n7",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2020-initial-mnd.pdf",
      "bytes": 7660215,
      "sha256": "5d722976359a6fbc19bc6fe60387c4093dccef20b7dfef13b33d50aedb9a36a2"
    },
    {
      "id": "ceqanet_original_nod",
      "title": "MUSD Notice of Determination",
      "publisher": "California State Clearinghouse",
      "document_date": "2020-11-05",
      "url": "https://ceqanet.lci.ca.gov/2020080439/4",
      "status": "indexed"
    },
    {
      "id": "ceqanet_subsequent_mnd",
      "title": "Subsequent Mitigated Negative Declaration",
      "publisher": "California State Clearinghouse",
      "document_date": "2023-05-11",
      "url": "https://ceqanet.lci.ca.gov/2020080439/5",
      "status": "captured",
      "attachment_url": "https://ceqanet.lci.ca.gov/2020080439/5/Attachment/3Xjr17",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2023-draft-subsequent-mnd.pdf",
      "bytes": 1848986,
      "sha256": "38cbd858a135fdfdc384c67f802f1cd92747bdba9e8fb8fa7f70bb9b04091320"
    },
    {
      "id": "ceqanet_final_subsequent_mnd",
      "title": "Final Subsequent Mitigated Negative Declaration",
      "publisher": "California State Clearinghouse",
      "document_date": "2023-06-30",
      "url": "https://ceqanet.lci.ca.gov/2020080439/7",
      "status": "indexed"
    },
    {
      "id": "ceqanet_musd_2023_nod",
      "title": "MUSD Notice of Determination - Modified Project",
      "publisher": "California State Clearinghouse",
      "document_date": "2023-07-05",
      "url": "https://ceqanet.lci.ca.gov/2020080439/8",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/ddw-recovery/2023-07-05-musd-project-nod-ceqanet.pdf",
      "bytes": 56713,
      "sha256": "68d2fdcbe04c802413713f294f4afd4f76236033302e20a7d50d93caf5816fb2"
    },
    {
      "id": "ceqanet_county_2024_nod",
      "title": "County Notice of Determination - U_2023-0004",
      "publisher": "California State Clearinghouse",
      "document_date": "2024-04-04",
      "url": "https://ceqanet.lci.ca.gov/2020080439/9",
      "status": "indexed"
    },
    {
      "id": "ceqanet_2024_addendum_nod",
      "title": "MUSD Notice of Determination - 2024 Addendum",
      "publisher": "California State Clearinghouse",
      "document_date": "2024-12-09",
      "url": "https://ceqanet.lci.ca.gov/2020080439/10",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/ddw-recovery/2024-11-26-musd-project-nod.pdf",
      "bytes": 69042,
      "sha256": "a01ef57348d070f73c7acd6a186e5b9c0af8d4d1e76f41f1b2c38b5b94aaf83f"
    },
    {
      "id": "ceqanet_water_supply_amendment",
      "title": "State Water Board Water-Supply Permit Amendment",
      "publisher": "California State Clearinghouse",
      "document_date": "2025-12-01",
      "url": "https://ceqanet.lci.ca.gov/2020080439/12",
      "status": "captured",
      "attachment_url": "https://ceqanet.lci.ca.gov/2020080439/12/Attachment/aSsaxb",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2025-ddw-permit-amendment-nod.pdf",
      "bytes": 114080,
      "sha256": "4cb6e921a5d23caa0e4c7ffa5921e9f99e9bd2265ef91e58ab403b341a8bc7d5",
      "note": "The attachment is the signed Notice of Determination, not the amended permit. It states that permit-approval records are available upon request from the DDW Santa Rosa office. Its PDF metadata names an unrelated Floriston project, but the visible body and CEQAnet record identify CA2300584; treat the metadata as a reused-template anomaly."
    },
    {
      "id": "rwqcb_noa",
      "title": "Notice of Applicability - MUSD Water System Restoration Project",
      "publisher": "North Coast Regional Water Quality Control Board",
      "document_date": "2026-05-28",
      "url": "https://www.waterboards.ca.gov/northcoast/board_decisions/water_quality_certification/pdf/2026/musdrst_noa.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/musdrst_noa.pdf",
      "bytes": 759991,
      "sha256": "d79136fd0b46d3e414bde6d5e5a1ed48e65820ce61c90e467b75880ac20fc8f9"
    },
    {
      "id": "ceqanet_2026_addendum",
      "title": "Subsequent MND Addendum Approval",
      "publisher": "California State Clearinghouse",
      "document_date": "2026-05-07",
      "url": "https://ceqanet.lci.ca.gov/2020080439/13",
      "status": "indexed"
    },
    {
      "id": "ceqanet_cdfw_nod",
      "title": "CDFW Notice of Determination and Streambed Alteration Agreement",
      "publisher": "California Department of Fish and Wildlife",
      "document_date": "2026-07-15",
      "url": "https://ceqanet.lci.ca.gov/2020080439/14",
      "status": "indexed"
    },
    {
      "id": "ceqanet_2026_revised_addendum",
      "title": "Subsequent MND Revised Addendum Approval",
      "publisher": "California State Clearinghouse",
      "document_date": "2026-07-16",
      "url": "https://ceqanet.lci.ca.gov/2020080439/15",
      "status": "indexed"
    },
    {
      "id": "public_comment_maeder",
      "title": "Public Comment - Maeder",
      "publisher": "Mendocino County",
      "document_id": 79258,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79258",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_orourke",
      "title": "Public Comment - O'Rourke",
      "publisher": "Mendocino County",
      "document_id": 79260,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79260",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_yeh_1",
      "title": "Public Comment - Yeh",
      "publisher": "Mendocino County",
      "document_id": 79262,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79262",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_aranguren",
      "title": "Public Comment - Aranguren",
      "publisher": "Mendocino County",
      "document_id": 79276,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79276",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_request_renotice",
      "title": "Public Request to Re-Notice",
      "publisher": "Mendocino County",
      "document_id": 79278,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79278",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_yeh_2",
      "title": "Public Comment - Yeh (second submission)",
      "publisher": "Mendocino County",
      "document_id": 79286,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79286",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_jung",
      "title": "Public Comment - Jung",
      "publisher": "Mendocino County",
      "document_id": 79290,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79290",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_orourke_2",
      "title": "Public Comment - M. O'Rourke",
      "publisher": "Mendocino County",
      "document_id": 79296,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79296",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_stavely",
      "title": "Public Comment - Stavely",
      "publisher": "Mendocino County",
      "document_id": 79320,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79320",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_yeh_3",
      "title": "Public Comment - Yeh (third submission)",
      "publisher": "Mendocino County",
      "document_id": 79322,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79322",
      "status": "identified_unretrieved"
    },
    {
      "id": "public_comment_walton",
      "title": "Public Comment - Walton",
      "publisher": "Mendocino County",
      "document_id": 79324,
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/79324",
      "status": "identified_unretrieved"
    },
    {
      "id": "hearing_video_2024_12_05",
      "title": "Planning Commission - December 5, 2024",
      "publisher": "Mendocino County",
      "url": "https://archive.org/details/comenca-Planning_Commission_12_5_2024",
      "status": "available_not_transcribed"
    },
    {
      "id": "hearing_video_2024_12_19",
      "title": "Planning Commission - December 19, 2024",
      "publisher": "Mendocino County",
      "url": "https://archive.org/details/comenca-Planning_Commission_12_19_2024",
      "status": "available_not_transcribed"
    },
    {
      "id": "hearing_video_2026_08_20",
      "title": "Planning Commission - August 20, 2026",
      "publisher": "Mendocino County",
      "url": "https://www.youtube.com/watch?v=GdWCwPeIcX8",
      "status": "captured_transcribed",
      "capture_path": "captures/cases/UM_2025-0004/august-20-2026-hearing.m4a",
      "bytes": 147725053,
      "sha256": "d55c3f390bef4a88e5eedc6fcd9166fa83d84e6dc5ce7073970f32e0f53e4769",
      "transcript": {
        "type": "locally_generated_not_official",
        "path": "captures/cases/UM_2025-0004/transcript/august-20-2026-hearing.json",
        "sha256": "443ddd5a7a3e4bc32406c709ac25758bb242337a7a7f89d726cd10d549d8d519"
      }
    },
    {
      "id": "musd_2023_final_subsequent_mnd",
      "title": "Final Subsequent Mitigated Negative Declaration",
      "publisher": "Mendocino Unified School District",
      "document_date": "2023-06-30",
      "url": "https://www.mendocinousd.org/files/user/160/file/Final-Subsequent-MND-for-MUSD-Water-System-Project.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2023-final-subsequent-mnd.pdf",
      "bytes": 11225277,
      "sha256": "02c3092324398da47d350d81ab2f5fe135cfee9699408a123da4944a4a1608e3"
    },
    {
      "id": "mccsd_musd_2024_mou",
      "title": "Memorandum of Understanding Between MCCSD and MUSD",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2024-11-25",
      "url": "https://www.mccsd.com/files/c8044adca/signed+MOU+%282%29.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2024-mccsd-musd-mou.pdf",
      "bytes": 349301,
      "sha256": "1bc6337e167161dfc46626583d5a0f1bbf25ff99bdc604eb4fd5b80e8c8a415b",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/2024-mccsd-musd-mou.ocr.txt",
        "sha256": "0a02e10977d545a2ed0ca251347b2f7b86318a9a0f5e4576fc35da76d70ac98e"
      }
    },
    {
      "id": "mccsd_2020_msr_soi",
      "title": "MCCSD Municipal Service Review and Sphere of Influence Update",
      "publisher": "Mendocino LAFCo",
      "document_date": 2020,
      "url": "https://www.mendolafco.org/files/a43d86571/MCCSD+MSR-SOI+Update+2020_Final.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2020-mccsd-msr-soi.pdf",
      "bytes": 6730536,
      "sha256": "3e21c965960c84b4b5d6f0b01049f9230323d58bda285d02b61145b16e622cf3"
    },
    {
      "id": "mccsd_2020_water_shortage_ordinance",
      "title": "Ordinance 2020-2 - Water Shortage Contingency Plan Ordinance",
      "publisher": "Mendocino City Community Services District",
      "document_date": 2020,
      "url": "https://mccsd.specialdistrict.org/files/3bd9918b9/ORD+NO+2020-2+WSCP.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2020-mccsd-water-shortage-plan.pdf",
      "bytes": 124282,
      "sha256": "de949ebce29cdffd38d7773e9ec4d6d346268433169d664e195446985c8e038f",
      "note": "Enforcement ordinance adopted alongside the separate Water Shortage Contingency Plan. It authorizes declarations, restrictions, allotment reductions, and penalties but refers to Resolution 2020-269 for adoption of the plan containing the drought indicators and management actions."
    },
    {
      "id": "mccsd_2020_water_shortage_plan",
      "title": "Water Shortage Contingency Plan",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2020-05-11",
      "url": "https://www.mccsd.com/files/ce188b244/4-17-2020+Water+Shortage+Contingency+Plan.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2020-04-17-mccsd-water-shortage-contingency-plan.pdf",
      "bytes": 838762,
      "sha256": "1a249d1d36c8719044c968e58f5b121830fed58ab865427e4ecce85278001001",
      "note": "Official 31-page plan marked \"Adopted May 11, 2020.\" It contains rainfall and indicator-well criteria for Stages 1-4 and the corresponding management actions. The filename retains its April 17 draft date; Resolution 2020-269, cited by Ordinance 2020-2 as the adopting instrument, has not yet been captured, and later plan modifications have not been ruled out."
    },
    {
      "id": "ddw_dfa_2023_comment_letter",
      "title": "DDW and Division of Financial Assistance Comments on Subsequent MND",
      "publisher": "State Water Resources Control Board",
      "document_date": "2023-06-20",
      "url": "https://ceqanet.lci.ca.gov/2020080439/5/Attachment/q7G9Qj",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2023-ddw-dfa-comment-letter.pdf",
      "bytes": 578809,
      "sha256": "536d489fe2468f5cc4dcb9003cf848544b8f73e13cae597842b4c1758d7a4a77",
      "note": "Identifies DWSRF agreement C-06-2300584-001C, requires a permit amendment, and asks for an emergency hauled-water operating plan."
    },
    {
      "id": "ghd_2023_hydrogeologic_report",
      "title": "Hydrogeologic Report - Drought Tolerance Emergency Water Supply and Storage Improvements",
      "publisher": "GHD / Mendocino Unified School District",
      "document_date": "2023-04-19",
      "url": "https://ceqanet.lci.ca.gov/2020080439/5/Attachment/juzK3Y",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2023-ghd-hydrogeologic-report.pdf",
      "bytes": 8564670,
      "sha256": "deb0126efd89e6b226d0939776deccdd9bd9821213c57c4411242054fcc3be30"
    },
    {
      "id": "ddw_2021_service_area",
      "title": "CA2300584 Drinking Water System Area Boundary",
      "publisher": "State Water Resources Control Board",
      "document_date": "2021-10-22",
      "url": "https://gispublic.waterboards.ca.gov/portalserver/rest/services/Drinking_Water/California_Drinking_Water_System_Area_Boundaries/FeatureServer/0/query?where=WATER_SYSTEM_NUMBER%3D%27CA2300584%27&outFields=%2A&returnGeometry=true&outSR=4326&f=geojson",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2021-ddw-service-area.geojson",
      "bytes": 2875,
      "sha256": "86a64e2b2ca32afbee6fb7cb893a8dbc7357a12f4bc6e7fe5f9d2208b3cd2ea3",
      "note": "Verified two-part MultiPolygon last edited in October 2021. The Water Board warns that this layer is a general representation, may be outdated, and is not a binding legal document."
    },
    {
      "id": "county_2024_conditions_memo",
      "title": "Analysis of Proposed Additional Special Conditions for UM_2024-0008",
      "publisher": "Mendocino County Planning and Building Services",
      "document_date": "2024-12-19",
      "url": "https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=JFE%3A2412170831401453&ActivityNo=UM_2024-0008",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/conditions/2024-12-new-conditions-memo.pdf",
      "bytes": 153106,
      "sha256": "2a61db81b4c09938470c21cef4e8a32820c53f7aa147989bb202888ad0c5bbea",
      "note": "Staff analysis of Commissioner Jones's proposed additions. It recommends revised drought, hydrology, seasonal pumping, irrigation, eligibility, reserve, future-development, and pump-test conditions."
    },
    {
      "id": "county_2024_resolution_redline",
      "title": "UM_2024-0008 Draft Redline Resolution for December 19, 2024",
      "publisher": "Mendocino County Planning and Building Services",
      "document_date": "2024-12-19",
      "url": "https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=JFE%3A2412170831401452&ActivityNo=UM_2024-0008",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/conditions/2024-12-19-draft-redline.pdf",
      "bytes": 127399,
      "sha256": "a76dfbc920e4368651fd86e474a20ad8fe88823e47c799105480c60a9d89ffe0",
      "version_of": "UM_2024-0008_resolution",
      "version": "pre_adoption_redline",
      "condition_count": 22
    },
    {
      "id": "county_pc_2024_0019",
      "title": "Resolution PC 2024-0019 for UM_2024-0008",
      "publisher": "Mendocino County Planning Commission",
      "document_date": "2024-12-19",
      "url": "https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=JFE%3A2501030815526995&ActivityNo=PC_2024-0019",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/conditions/2024-pc-2024-0019-adopted.pdf",
      "bytes": 522597,
      "sha256": "ade3e62398cb3b40e2e5a1109759e8cc69eca31362ba8cc5da4248da12f54150",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/conditions/2024-pc-2024-0019-adopted.ocr.txt",
        "sha256": "30829218df1108aa8cbe9ef2770462b0c0d4b49c268d8786687f1ab2b977ebe7"
      },
      "version_of": "UM_2024-0008_resolution",
      "version": "adopted_signed",
      "condition_count": 21,
      "note": "Signed adopted resolution. Compared with the 22-condition redline, the adopted set removes a separate stored-water eligibility condition, consolidates the eligibility and reserve provisions, and adds the final non-drought-development restriction as Condition 21."
    },
    {
      "id": "county_exhibit_i",
      "title": "Exhibit I - Emergency Water Service Area",
      "publisher": "Mendocino County / Mendocino Unified School District",
      "document_date": "2024-12",
      "url": "https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=JFE%3A2412170831411454&ActivityNo=UM_2024-0008",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/boundaries/2024-exhibit-i-ewsa.pdf",
      "bytes": 1494183,
      "sha256": "eb10629ce4d15ded1a66fdd644f0048e733d31ad94510be4d76964e1f7940e9d",
      "note": "Permit-condition eligibility map without parcel boundaries. Footer identifies ArcGIS Pro project 12571432_MCCSD_Figures.aprx, layout 12571432_EWSA, and creator ethompson3."
    },
    {
      "id": "lafco_2020_resolution_2020_21_01",
      "title": "LAFCo Resolution 2020-21-01 - MCCSD MSR and Sphere of Influence Update",
      "publisher": "Mendocino LAFCo",
      "document_date": "2020-08-03",
      "url": "https://www.mendolafco.org/files/b02f8b2b5/2020-21-01%2C+MCCSD+MSR-SOI++%28signed%29.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/boundaries/2020-lafco-resolution-2020-21-01.pdf",
      "bytes": 2219712,
      "sha256": "1dde1a5739c288070f55590d3cfa1c239cf2151c58deb2ccfeda0098be69aa77",
      "note": "Signed action making the MCCSD sphere coterminous with its jurisdictional boundary. It expressly grants no new municipal service powers or areas."
    },
    {
      "id": "county_2026_mccsd_boundary",
      "title": "Mendocino County GIS - MCCSD Boundary",
      "publisher": "Mendocino County GIS",
      "document_date": 2026,
      "url": "https://services5.arcgis.com/8y4r60VTvWj2wnDH/arcgis/rest/services/Community_Services_Districts/FeatureServer/0/query?where=OBJECTID%3D46&outFields=OBJECTID%2CNAME%2COWNER%2CCITY&returnGeometry=true&outSR=4326&f=geojson",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/boundaries/2026-county-mccsd-boundary.geojson",
      "bytes": 36367,
      "sha256": "ac8aea155fddbb1c5cb38e78367260b543ac86a774f227b78412dd420d5eabe7",
      "note": "Official current County GIS geometry for OBJECTID 46. It can be overlaid with current assessor parcels but is not the source of the 2024 Exhibit I polygon and does not include its outer emergency eligibility area."
    },
    {
      "id": "nextrequest_2021_hauled_water",
      "title": "County of Mendocino Water Hauling Recap",
      "publisher": "Mendocino County",
      "document_date": "2023-06-21",
      "url": "https://mendocinocounty.nextrequest.com/documents/21849950",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/pra/2021-hauled-water-response.pdf",
      "bytes": 108291,
      "sha256": "a459a85ed9a185eeee551dd5ad1df3b97085cef3c1183eeefdfb4834b484e4f9",
      "note": "Released in public request 23-445. Reports 1,291,100 gallons hauled from Ukiah to Fort Bragg and 414,500 gallons delivered to Mendocino in the September 2021-August 2022 residential summary. The document's destination table totals 1,294,402 gallons, 3,000 more than its stated residential grand total, so the discrepancy is preserved rather than normalized."
    },
    {
      "id": "musd_2023_response_and_funding_agreements",
      "title": "Water System Reconstruction Project - Response to Comments and Funding Agreements",
      "publisher": "Mendocino Unified School District",
      "document_date": "2023-06",
      "url": "https://www.mendocinousd.org/files/user/160/file/MUSD-Water-System-Project-Response-to-Comments-on-Subsequent-MND.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2023-response-to-comments-and-agreements.pdf",
      "bytes": 13440878,
      "sha256": "70662383a3d64709032923575be0fb014f2066fb0695ceedfec89d72485998a6",
      "note": "Appendix B contains executed State Water Board financing agreement D2202005 for project 2300584-001C. Appendix C contains DWR Agreement 4600014624 Amendment 1 and Exhibits A-M. Appendix D contains the superseded April 2023 MUSD-MCCSD MOU."
    },
    {
      "id": "musd_2026_project_status",
      "title": "MUSD Water Supply and Storage Project - Project Status Update",
      "publisher": "Mendocino Unified School District",
      "document_date": "2026-03-06",
      "url": "https://www.mendocinousd.org/files/user/1/file/MARCH-2026-Item-8_1.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2026-project-status-and-dwr-letter.pdf",
      "bytes": 226179,
      "sha256": "f16d9f046a263b96b6f865e1db0a5a0a77cab04e1bfe6f24723e3b840ca0a580",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/2026-project-status-and-dwr-letter.ocr.txt",
        "sha256": "cf63180ed10d2884043501ea82646dd80c0eaada11777bec1d3186e19bc0d9a1"
      },
      "note": "Includes DWR's March 5, 2026 funding-expiration letter. Its reference to the latest amendment and March 31, 2026 work deadline proves a later DWR amendment exists beyond the publicly captured May 2023 Amendment 1."
    },
    {
      "id": "ccc_2016_town_lcp_report",
      "title": "Mendocino Town LCP Update - October 2016 Staff Report and Addendum",
      "publisher": "California Coastal Commission",
      "document_date": "2016-10-04",
      "url": "https://documents.coastal.ca.gov/reports/2016/10/w13a-10-2016.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2016-10-ccc-mendocino-town-lcp.pdf",
      "bytes": 9035463,
      "sha256": "68406dd893e2e64508f152a47b8d5463c1108c93aebfab1cf78f20aaab2277c5",
      "note": "Preliminary Commission review of the comprehensive Town LCP update, including public correspondence received after the September 23 report."
    },
    {
      "id": "ccc_2017_town_lcp_report",
      "title": "Mendocino Town LCP Update - June 2017 Staff Report",
      "publisher": "California Coastal Commission",
      "document_date": "2017-05-26",
      "url": "https://documents.coastal.ca.gov/reports/2017/6/th9f/th9f-6-2017-report.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2017-06-ccc-mendocino-town-lcp.pdf",
      "bytes": 831080,
      "sha256": "783f3bb536ef25e368a5025b0440f2298928b60c4ff71205d3412aee7dcb0fe9",
      "note": "Final certification recommendation. At PDF page 82 it states that the County had never applied to incorporate MCCSD groundwater-extraction permit provisions into the certified Town LCP."
    },
    {
      "id": "ccc_2017_town_lcp_exhibits",
      "title": "Mendocino Town LCP Update - June 2017 Exhibits",
      "publisher": "California Coastal Commission",
      "document_date": "2017-05-26",
      "url": "https://documents.coastal.ca.gov/reports/2017/6/th9f/th9f-6-2017-exhibits.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2017-06-ccc-mendocino-town-lcp-exhibits.pdf",
      "bytes": 37369644,
      "sha256": "077990570606707a56325d8ac0740333d89ec2d62560d21dcca2f4418127a156",
      "note": "Official 424-page compilation: transmittal at pages 4-5; consistency analysis at 6-13; Resolution 15-180 at 14-17; County transmittal correspondence at 18-19; water-supply analysis excerpts at 20-41; 2006 drought-scenarios memorandum at 42-66; and pre- and post-report correspondence at 85-424."
    },
    {
      "id": "ccc_2017_town_lcp_appendices",
      "title": "Mendocino Town LCP Update - June 2017 Appendices",
      "publisher": "California Coastal Commission",
      "document_date": "2017-05-26",
      "url": "https://documents.coastal.ca.gov/reports/2017/6/th9f/th9f-6-2017-appendices.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2017-06-ccc-mendocino-town-lcp-appendices.pdf",
      "bytes": 13479594,
      "sha256": "052104eca9a4eda275843a50ee96df3d97ab996f8a2fd4db55556f1b5190541b",
      "note": "Official 584-page compilation of the proposed LUP and IP text, maps, administrative record index, agency coordination, MCCSD water-demand standards, and water-demand and build-out analyses."
    },
    {
      "id": "ccc_2017_town_lcp_addenda",
      "title": "Mendocino Town LCP Update - June 2017 Addenda",
      "publisher": "California Coastal Commission",
      "document_date": "2017-06-07",
      "url": "https://documents.coastal.ca.gov/reports/2017/6/th9f/th9f-6-2017-addenda.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2017-06-ccc-mendocino-town-lcp-addenda.pdf",
      "bytes": 178170,
      "sha256": "76899a6de654c79584d6ce03b6a7ab0f75bc364bb0914243b0d9dfdc9dd62062"
    },
    {
      "id": "ccc_2017_town_lcp_certification",
      "title": "Mendocino Town LCP Update - Legal Adequacy Determination",
      "publisher": "California Coastal Commission",
      "document_date": "2017-10-27",
      "url": "https://documents.coastal.ca.gov/reports/2017/11/w21f/w21f-11-2017-report.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/2017-11-ccc-mendocino-town-lcp.pdf",
      "bytes": 130158,
      "sha256": "880e61d5a3e7e25c5c54fa9fa469e743a7ada82b4c8d9f6a64c66837e376e277",
      "note": "Records the County's October 17 acceptance of all suggested modifications and the Executive Director's legal-adequacy determination."
    },
    {
      "id": "county_mendocino_town_plan",
      "title": "Mendocino Town Plan",
      "publisher": "Mendocino County",
      "document_date": "2017-11-08",
      "url": "https://www.mendocinocounty.org/home/showpublisheddocument/29428/637023534722670000",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/mendocino-town-plan.pdf",
      "bytes": 2130244,
      "sha256": "ba25b676ed6be2d387e462d72b00f184df53361e5e6a3509af7cc1a6584ab5eb",
      "note": "Current County publication of the certified Mendocino Town LUP."
    },
    {
      "id": "county_ordinance_4395",
      "title": "Ordinance 4395 - Mendocino Town Zoning Code Amendments",
      "publisher": "Mendocino County Board of Supervisors",
      "document_date": "2017-10-17",
      "url": "https://www.mendocinocounty.gov/departments/planning-building-services/planning-division/local-coastal-program",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/town-lcp/ordinance-4395.pdf",
      "bytes": 9108447,
      "sha256": "4e297a47a1875f4e246ca02a375a541386d9dc0b0152ab2d5a073d73f341de0b",
      "note": "Signed ordinance and 304-page Exhibit A adopting the Commission's suggested modifications to Division III of Title 20."
    },
    {
      "id": "nextrequest_22_583_mccsd_2018_letter",
      "title": "MCCSD Comments on CDP_2018-0012",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2018-12-20",
      "url": "https://mendocinocounty.nextrequest.com/documents/14628657",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/pra/nextrequest-documents/14628657-20181220 email MCCSD Comments.pdf",
      "bytes": 64824,
      "sha256": "b66024e73a09620d0030c05979fb33fccb2e92664bfaf523a95090b694158dba",
      "note": "Prior PRA production documenting MCCSD hydrological-study approval, groundwater-extraction allotment, permit requirement, and sewer capacity."
    },
    {
      "id": "nextrequest_22_583_mccsd_2019_comment",
      "title": "MCCSD Agency Comment on CDP_2018-0012",
      "publisher": "Mendocino County Planning and Building Services",
      "document_date": "2019-10-14",
      "url": "https://mendocinocounty.nextrequest.com/documents/14628653",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/pra/nextrequest-documents/14628653-CDP-2018-0012 MCCSD Comment 20191014.pdf",
      "bytes": 1130907,
      "sha256": "5494f37653713eeb08a5bbede906e94d7a25b5a39903a641511bfef314e8da51",
      "note": "County agency referral bearing MCCSD's handwritten groundwater allotment and future Groundwater Extraction Permit comments."
    },
    {
      "id": "nextrequest_22_583_mccsd_drought_email",
      "title": "CDP_2018-0012 and MCCSD Stage 4 Drought Email",
      "publisher": "Mendocino County / Mendocino City Community Services District",
      "document_date": "2021-11-23",
      "url": "https://mendocinocounty.nextrequest.com/documents/14628659",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/pra/nextrequest-documents/14628659-RE CDP_2018-0012 Sheppard and MCCSD Stage 4 drought.pdf",
      "bytes": 23846,
      "sha256": "c9d67281a389b067bd66fd1c72555e9cfaeb6dad9d1284be551f7717802a190f",
      "note": "Shows County staff postponing a coastal-permit hearing while MCCSD's Stage 4 shortage prevented issuance of a groundwater-extraction permit."
    },
    {
      "id": "nextrequest_22_583_mccsd_2022_letter",
      "title": "MCCSD Water and Sewer Determination for CDP_2018-0012",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2022-03-23",
      "url": "https://mendocinocounty.nextrequest.com/documents/14628663",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/pra/nextrequest-documents/14628663-CDP_2018-0012 MCCSD Water Sewer March 2022.pdf",
      "bytes": 58203,
      "sha256": "f704db9a32b69fd2b7b7e05fb1b03b725c9a332aa40c2f364fc0cbc148f0ddaf",
      "note": "Confirms MCCSD approval of the Groundwater Extraction Permit application, 260-gallon-per-day allotment, hydrological-study review, and sewer rights."
    },
    {
      "id": "mccsd_water_code_10700_10717",
      "title": "California Water Code §§10700–10717 - Mendocino Groundwater Resources",
      "publisher": "California Legislature / Mendocino City Community Services District",
      "document_date": 2005,
      "url": "https://www.mccsd.com/files/61ad06df5/CALIFORNIA+WATER+CODE+10700-10717.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/water-code-10700-10717.pdf",
      "bytes": 63336,
      "sha256": "2aa5c67894a10edcee627d65e6772e948878bc1ff1df0c8991db0f38dc098817",
      "note": "MCCSD's official publication of the special groundwater statute. Section 10707 authorizes a groundwater-purpose JPA; section 10717 terminates these special powers upon implementation of a municipal central water system."
    },
    {
      "id": "lafco_2005_csd_powers",
      "title": "LAFCo CSD Powers Determination Following SB 135",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2005-12-29",
      "url": "https://www.mccsd.com/files/57bb38915/2005-12-29+LAFCo+CSD+Powers+Determinatin+Letter+Per+SB+135.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/2005-lafco-csd-powers-determination.pdf",
      "bytes": 173522,
      "sha256": "6eb7ca22588930d8c18d482910fe693c2190da510665e8a0747112fcc442276c",
      "note": "Official pre-2006 service inventory identifying MCCSD water services and its groundwater-management program as active rather than latent."
    },
    {
      "id": "lafco_2022_groundwater_authority",
      "title": "LAFCo Letter Confirming MCCSD Water and Groundwater Powers",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2022-11-22",
      "url": "https://www.mccsd.com/files/1cdbeff54/11-22-22+letter+from+LAFCO.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/2022-lafco-letter.pdf",
      "bytes": 124848,
      "sha256": "bec58a68b98c6c7bd8a2eabe4960a3c38114a445a8a3db9d009fb7148a6e6ea0",
      "note": "Traces the 1985 election, AB 786, Ordinance 90-1, SB 135, and LAFCo's conclusion that MCCSD's water and groundwater powers remain active."
    },
    {
      "id": "mccsd_ordinance_2020_01",
      "title": "Ordinance 2020-01 - Groundwater Extraction Permit Program",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2020-05-18",
      "url": "https://www.mccsd.com/files/fb479f121/ORD%202020-01%20GWEP.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/2020-ordinance-01-gwep.pdf",
      "bytes": 302033,
      "sha256": "4b5d1b62590407da6dd7ac34041160cfe708a04bce3d4b58afdb07dea6c29d3e",
      "note": "Current captured GWEP rules governing studies, extraction allotments, meters, County referrals, violations, appeals, and emergency permits."
    },
    {
      "id": "county_1989_coastal_groundwater_guidelines",
      "title": "Coastal Groundwater Development Guidelines",
      "publisher": "Mendocino County Environmental Health",
      "document_date": "1989-07",
      "document_id": "County published documents 2700 and 2780",
      "url": "https://www.mendocinocounty.gov/home/showpublisheddocument/2700/636232201594400000",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/1989-mendocino-county-coastal-groundwater-development-guidelines.pdf",
      "bytes": 405098,
      "sha256": "8cb2308c4279d2da0629512621fe7658ae95cc954c9e25210f1edd1605d22a62",
      "note": "Official 31-page County publication prepared by Questa Engineering Corporation (Project 86146), dated July 1989 and marked \"BOS Adopted on November 21, 1989.\" The live County binary returned 403 from this environment, so the identical official binary was recovered from the Internet Archive's 2025-02-17 capture. The County land-use page also links published document 2780; archive metadata gives documents 2700 and 2780 the same content digest. At the August 20, 2026 hearing, GHD's Matt Kennedy named this guideline and read its adjoining-well adverse effect criteria."
    },
    {
      "id": "mccsd_2020_groundwater_update",
      "title": "Mendocino 2020 Groundwater Management Update",
      "publisher": "Todd Groundwater / Mendocino City Community Services District",
      "document_date": "2021-06-10",
      "url": "https://www.mccsd.com/files/abefe0a27/ADMIN+DRAFT+Mendo_2020-GWupdate_Jun10.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/2020-groundwater-update.pdf",
      "bytes": 3063276,
      "sha256": "56ef0d65736f77dbba760bee863e2e77aa24019cd4b7420847c5d9cd82775c99",
      "note": "Technical explanation of the aquifer, groundwater model, extraction program, metered demand, drought stages, and 2020–2021 conditions."
    },
    {
      "id": "ca_drinking_water_lawbook_2026",
      "title": "California Safe Drinking Water Laws",
      "publisher": "State Water Resources Control Board",
      "document_date": "2026-02-10",
      "url": "https://water.waterboards.ca.gov/laws_regulations/docs/drinking-water-code.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/2026-california-drinking-water-lawbook.pdf",
      "bytes": 2426526,
      "sha256": "b22f38c8960189c717bdb3ec55d331933f4a248a0be1b78b460cd60be4e145bd",
      "note": "Current 210-page State Water Board compilation used to distinguish public water system regulation from local-agency governance and service powers."
    },
    {
      "id": "ca_water_code_13198_2026",
      "title": "California Water Code § 13198",
      "publisher": "California Legislative Information",
      "document_date": "2026-08-22",
      "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=13198.&lawCode=WAT",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/2026-california-water-code-13198.html",
      "bytes": 165975,
      "sha256": "5c497ef2df869f97f3279b271b884452ad0cf36e26332bb993460b9b3a2bd465",
      "note": "Official current section capture. Subdivision (a) defines the two drought scenarios; subdivision (c) defines interim or immediate relief, including hauled water, temporary tanks, emergency interties, wells, and certain permanent connections. The page states that the section was amended by Statutes 2023, chapter 51, section 36, effective July 10, 2023."
    },
    {
      "id": "state_controller_jpa_guide",
      "title": "Government Code Sections Pertaining to Joint Powers Agreements",
      "publisher": "California State Controller's Office",
      "document_date": "2022-02-03",
      "url": "https://sco.ca.gov/Files-ARD-Local/LocRep/Joint_Powers_Agreement_Revised_2.3.22ADA.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/joint-powers-filing-guide.pdf",
      "bytes": 111129,
      "sha256": "8740e3a053e79c2703bb6066b8af91dafa616b5c2751d009d37d8b9639433b44",
      "note": "Official filing, financial-reporting, and audit requirements for separate-entity joint powers authorities."
    },
    {
      "id": "ddw_public_water_system_guide",
      "title": "What Is a Public Water System?",
      "publisher": "State Water Resources Control Board, Division of Drinking Water",
      "document_date": "2022-01-31",
      "url": "https://www.waterboards.ca.gov/drinking_water/certlic/drinkingwater/documents/waterpartnerships/what_is_a_public_water_sys.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/ddw-what-is-a-public-water-system.pdf",
      "bytes": 388076,
      "sha256": "6b32bdeeb83fac6df6b208c9fffa79f2cd0083c848951c6614b4611293b4ec53",
      "note": "Explains that schools can be nontransient noncommunity systems and that public-water-system status does not necessarily mean public ownership."
    },
    {
      "id": "ddw_permit_application",
      "title": "Application for Domestic Water Supply Permit",
      "publisher": "State Water Resources Control Board, Division of Drinking Water",
      "document_date": "2024-09-26",
      "url": "https://www.waterboards.ca.gov/drinking_water/certlic/drinkingwater/Documents/Permits/permit_application.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/ddw-permit-application.pdf",
      "bytes": 155314,
      "sha256": "78b90c007f1b6c0f62c1b289b10ee213059b50797df3756a371114d42fe9906f"
    },
    {
      "id": "ddw_amended_permit_application",
      "title": "Application for Domestic Water Supply Permit Amendment",
      "publisher": "State Water Resources Control Board, Division of Drinking Water",
      "document_date": "2020-12-16",
      "url": "https://www.waterboards.ca.gov/drinking_water/certlic/drinkingwater/Documents/Permits/amended_permit_application.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/authority/ddw-amended-permit-application.pdf",
      "bytes": 158787,
      "sha256": "a97fa007852e352ac5459e06eb0442ff122e06897a0d7f2fbc36b2fe84337005"
    },
    {
      "id": "mccsd_2012_groundwater_management_plan",
      "title": "Groundwater Management Plan and Programs",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2012-06-14",
      "url": "http://www.co.mendocino.ca.us/planning/pdf/MCCSD_Groundwater_Management_Plan_and_Programs_2012.pdf",
      "archive_url": "https://web.archive.org/web/20150908040618id_/http://www.co.mendocino.ca.us/planning/pdf/MCCSD_Groundwater_Management_Plan_and_Programs_2012.pdf",
      "status": "captured_from_internet_archive",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/MCCSD_Groundwater_Management_Plan_and_Programs_2012.pdf",
      "bytes": 5704080,
      "sha256": "0772e181af7a1bef992e0792d2f0b32aa1acdeca885deead78b02d04595249a6",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/archive-recovery/MCCSD_Groundwater_Management_Plan_and_Programs_2012.ocr.txt",
        "sha256": "9bcac5932213d7f342b4b99cddc8340b786907b86bba4c912324517e4c7370e5"
      },
      "note": "Complete 114-page official plan recovered from the County's former URL. Appendix A embeds Resolution 113 at PDF page 31, the AB 786 chapter law at page 32, and signed County-MCCSD Agreement 90-113 at pages 36-37. Appendix B embeds Ordinance 07-1. Appendix D embeds the 1997 recycled-water MOU at pages 73-74, Joint Resolution 97-1 at pages 75-76, and the January 2, 1990 County minute order at page 77. OCR is a finding aid; signatures, handwriting, and faint archival pages require review against the PDF image."
    },
    {
      "id": "mccsd_ordinance_2007_01",
      "title": "Ordinance 07-1 - Groundwater Extraction Permit Ordinance",
      "publisher": "Mendocino City Community Services District",
      "document_date": 2007,
      "url": "http://mccsd.com/pdf/ORD%2007-1%20Groundwater%20Extraction%20Permit.pdf",
      "archive_url": "https://web.archive.org/web/20161118142853id_/http://mccsd.com/pdf/ORD%2007-1%20Groundwater%20Extraction%20Permit.pdf",
      "status": "captured_from_internet_archive",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/ORD-07-1-Groundwater-Extraction-Permit.pdf",
      "bytes": 1899077,
      "sha256": "8ee0c35c414124b6a71c98582fb5a511aaea00b014635b38a053c52faf79837c",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/archive-recovery/ORD-07-1-Groundwater-Extraction-Permit.ocr.txt",
        "sha256": "b0e448907da5ec1f6871912a9653d2cd2a9bda40b3061cc60639b5f54e0cd4a0"
      },
      "note": "Archived official 27-page ordinance updating MCCSD's hydrological testing and groundwater-extraction permit procedures. OCR is a finding aid and exact clauses should be checked against the page image."
    },
    {
      "id": "mccsd_resolution_2012_224_minutes",
      "title": "MCCSD Special Meeting Minutes - Resolution 2012-224",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2012-07-09",
      "url": "https://www.mccsd.com/files/f8bc62af0/July-9-2012.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2012-07-09-mccsd-board-packet.pdf",
      "bytes": 35976,
      "sha256": "0b84e2a5caee34ee25f3803385b54e417cddd2b1fa73cb063b5d780f3feaadd2",
      "note": "Signed one-page special-meeting minutes showing unanimous adoption by the three directors present of Resolution 2012-224, incorporating additional groundwater programs into the 2012 plan."
    },
    {
      "id": "mccsd_musd_2023_mou",
      "title": "April 20, 2023 MUSD-MCCSD Water Supply and Storage Project MOU",
      "publisher": "Mendocino Unified School District / Mendocino City Community Services District",
      "document_date": "2023-04-20",
      "url": "https://www.mccsd.com/files/003159644/4-20-23+signed+MOU+with+MUSD.pdf",
      "status": "captured_superseded",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2023-04-20-signed-musd-mccsd-mou.pdf",
      "bytes": 375271,
      "sha256": "c83c3cf5c97113667c3eb18ad6f47427856413384063cdccd271c23751822ce4",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2023-04-20-signed-musd-mccsd-mou.ocr.txt",
        "sha256": "a6922cc424f0931413840477cde0aa4482fc8adeaa80c228aaf15836741995fe"
      },
      "note": "Signed potable-project agreement. MCCSD formally rescinded it on November 25, 2024, when adopting the revised MOU. OCR is a finding aid; signatures and handwritten dates require review against the PDF image."
    },
    {
      "id": "mccsd_2024_11_25_board_packet",
      "title": "MCCSD Board Packet - November 25, 2024",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2024-11-25",
      "url": "https://www.mccsd.com/files/549770ed4/P+BOARD+PACKET+11.25.24.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2024-11-25-mccsd-board-packet.pdf",
      "bytes": 1892008,
      "sha256": "ac545722cbae5d8a09061aaba349cfb8a05958e051f2ac46042453e0dfa37b83",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2024-11-25-mccsd-board-packet.ocr.txt",
        "sha256": "f50787bafffe1917e0d3021124cd4e20dc1f75131d539a5230670c264b366f63"
      },
      "note": "Contains the agenda, April 20, 2023 MOU, and proposed revised MOU. The packet establishes what was presented, not the action taken. OCR is a finding aid and exact wording should be checked against the page image."
    },
    {
      "id": "mccsd_2024_11_25_board_minutes",
      "title": "MCCSD Board Action Minutes - November 25, 2024",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2024-11-25",
      "url": "https://www.mccsd.com/files/27a7002b4/BOARD+MINUTES+11-25-24.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/archive-recovery/2024-11-25-mccsd-board-minutes.pdf",
      "bytes": 303744,
      "sha256": "f004b5d9d19112de805fc9004f96bfcf46ad466262be0784f2132e7eff6f9150",
      "note": "Records separate 4-0 votes, with Director Feiner absent, to rescind the April 20, 2023 MOU and adopt the revised Water Shortage Project MOU."
    },
    {
      "id": "mccsd_2022_08_29_board_minutes",
      "title": "MCCSD Board Action Minutes - August 29, 2022",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2022-08-29",
      "url": "https://mccsd.com/files/670b1456e/BOARD+MINUTES+8-29-22.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-08-29-mccsd-board-minutes.pdf",
      "bytes": 256915,
      "sha256": "279262a87af88bbe8dcfd71fca94de402530e4be8d0167d0e1862c86203db7b3",
      "note": "Agenda item 13a, PDF page 3, records a 5-0 vote approving the draft MUSD-MCCSD water-tank MOU."
    },
    {
      "id": "musd_2022_09_08_board_minutes",
      "title": "MUSD Board Minutes - September 8, 2022",
      "publisher": "Mendocino Unified School District",
      "document_date": "2022-09-08",
      "url": "https://www.mendocinousd.org/files/page/3016/9_8_22.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-09-08-musd-board-minutes.pdf",
      "bytes": 368902,
      "sha256": "f7b14aa7ff13bebe00a1cf5833640b7b530d01e2d222cb85399f6459d40a274e",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-09-08-musd-board-minutes.ocr.txt",
        "sha256": "1780d324ae0e642efa5f85b18fd5e56089b1345c0764ab3cfba936bdaad36b26"
      },
      "note": "Item 10.4 at PDF page 4 records a 5-0 vote approving the MOU for increased potable water storage. OCR is a finding aid."
    },
    {
      "id": "musd_2022_09_08_board_packet",
      "title": "MUSD Board Packet - September 8, 2022",
      "publisher": "Mendocino Unified School District",
      "document_date": "2022-09-08",
      "url": "https://www.mendocinousd.org/files/page/3015/9_8_2022_WEB.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-09-08-musd-board-packet.pdf",
      "bytes": 17043500,
      "sha256": "b67727cf23e9100b238f75b2084e8dcb35257b27ee8edddd1c929bb23f75306e",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-09-08-musd-board-packet.ocr.txt",
        "sha256": "8b55cd1bd19ba7e72d2fff7c83903fe6299c45578ef9f0c630a0dfa08fafff14"
      },
      "note": "The first potable-project MOU is embedded at PDF pages 332-335. It proposed MCCSD ownership and operation of the new tank and wells and MCCSD provision of emergency water to eligible customers. OCR is a finding aid; the embedded unsigned instrument is not the executed copy."
    },
    {
      "id": "mccsd_2022_10_03_board_minutes",
      "title": "MCCSD Special Board Minutes - October 3, 2022",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2022-10-03",
      "url": "https://mccsd.com/files/5e80a2948/SPECIAL+BOARD+MINUTES+10-3-22.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2022-10-03-mccsd-special-board-minutes.pdf",
      "bytes": 361651,
      "sha256": "e03362c0592557c16a5bdb0eb68b40f72c64116eebcdb436e815f9c4e6dd41db",
      "note": "Old Business item 5a records separate 5-0 votes rescinding the August draft approval and approving the final MOU previously adopted August 29."
    },
    {
      "id": "mccsd_2023_04_19_board_minutes",
      "title": "MCCSD Board Action Minutes - April 19, 2023",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2023-04-19",
      "url": "https://mccsd.com/files/e7ff61039/BOARD+MINUTES+4-19-23.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-19-mccsd-board-minutes.pdf",
      "bytes": 168773,
      "sha256": "2ed0e4c6fd36b3c49197df862e5c0910933fa27333e231fa1687530465ebb8e8",
      "note": "Item 9b records a 4-0 vote, with Director Feiner absent, adopting the updated MUSD-MCCSD MOU."
    },
    {
      "id": "mccsd_2023_04_19_board_packet",
      "title": "MCCSD Board Packet - April 19, 2023",
      "publisher": "Mendocino City Community Services District",
      "document_date": "2023-04-19",
      "url": "https://www.mccsd.com/files/003159644/4-19-23+PACKET.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-19-mccsd-board-packet.pdf",
      "bytes": 1576160,
      "sha256": "2fb029db6dc5d8c245c438bf56f1e7314647a4858db9cf0fbc5c4e2a71d11dfd",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-19-mccsd-board-packet.ocr.txt",
        "sha256": "46d0ad8cae7c2b1b16bcd0b135ce3fb2548dcea81fca14c8c17f612802cac70e"
      },
      "note": "Contains the proposed updated MOU at PDF pages 11-14 and a written opposition letter. The packet proves the text presented, not adoption."
    },
    {
      "id": "musd_2023_04_20_board_minutes",
      "title": "MUSD Board Minutes - April 20, 2023",
      "publisher": "Mendocino Unified School District",
      "document_date": "2023-04-20",
      "url": "https://www.mendocinousd.org/files/page/3016/Item_6.2A.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-20-musd-board-minutes.pdf",
      "bytes": 1686063,
      "sha256": "12dce9b25774ded7a173cd673fb6666b812d50ac9ef647e371ab8bf4e556477e",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-20-musd-board-minutes.ocr.txt",
        "sha256": "06622ade66411e49a45ad432c7fe17eea4126ee8cb2a6791a0c5a559234a62f6"
      },
      "note": "Item 9.1 at PDF page 4 records a 4-0-1 vote approving the updated potable-project MOU. OCR is a finding aid."
    },
    {
      "id": "musd_2023_04_20_board_packet",
      "title": "MUSD Board Packet - April 20, 2023",
      "publisher": "Mendocino Unified School District",
      "document_date": "2023-04-20",
      "url": "https://www.mendocinousd.org/files/page/3051/Apr_20_PACKET.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2023-04-20-musd-board-packet.pdf",
      "bytes": 9243766,
      "sha256": "bbe3b1dae650ce76740b95a9854dfebe6582ccd7f591f7aaaca70240f18f1d34",
      "note": "Includes the proposed updated MOU near the end of the packet. The packet establishes the text presented to MUSD; the minutes establish approval."
    },
    {
      "id": "musd_2024_11_21_board_minutes",
      "title": "MUSD Board Minutes - November 21, 2024",
      "publisher": "Mendocino Unified School District",
      "document_date": "2024-11-21",
      "url": "https://www.mendocinousd.org/files/page/3076/Item_7.2_B_November_21_minutes.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2024-11-21-musd-board-minutes.pdf",
      "bytes": 780403,
      "sha256": "af1e372ff227643ffb3da7e83fd1e2647b546a4b11be2fe7fd1a9de961d05f9d",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2024-11-21-musd-board-minutes.ocr.txt",
        "sha256": "7ddfde09bad3d056d3d1b8ae49d917771d2b66c860986393c4e18c2e93cddf65"
      },
      "note": "Items 9.3.1 and 9.3.2 at PDF page 4 record one 3-0 motion rescinding the April 2023 MOU and adopting the replacement. OCR is a finding aid."
    },
    {
      "id": "musd_2024_11_21_board_packet",
      "title": "MUSD Board Packet - November 21, 2024",
      "publisher": "Mendocino Unified School District",
      "document_date": "2024-11-21",
      "url": "https://www.mendocinousd.org/files/page/3075/11_21_24_web.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/musd-recovery/2024-11-21-musd-board-packet.pdf",
      "bytes": 6126927,
      "sha256": "ac1857f6dfd334c90f9503a6eb2751b05ef980d90e5001ecdd9f6adcc11f07dc",
      "note": "Contains the proposed replacement MOU. It proves the text presented to MUSD; the minutes establish the combined rescission/adoption vote."
    },
    {
      "id": "ca_assembly_final_history_1987_88",
      "title": "California Assembly Final History, 1987-88 Regular Session",
      "publisher": "Chief Clerk of the California State Assembly",
      "document_date": 1988,
      "url": "https://clerk.assembly.ca.gov/sites/clerk.assembly.ca.gov/files/archive/FinalHistory/1987/Volumes/878vol1_2ahr.PDF",
      "status": "captured_partially_ocr_indexed",
      "capture_path": "captures/cases/UM_2025-0004/water-law/historic-authority-recovery/ca-assembly-final-history-1987-88-asm-bills.pdf",
      "bytes": 80917736,
      "sha256": "6da100061a25bbc32624c5116aa2d6fa118ab2433636afde2516c402227e071c",
      "ocr": {
        "type": "locally_generated_tesseract",
        "path": "captures/cases/UM_2025-0004/water-law/historic-authority-recovery/ca-assembly-final-history-1987-88-asm-bills.ocr.txt",
        "sha256": "90960aaeefce81ea8d4d563bf1a687a878f1f71ca1b02aaa9b2b2881125f2500"
      },
      "note": "Official 3,170-page scanned history. PDF page 586 records AB 786's introduction, committee referrals, amendments, unanimous Assembly and Senate passage, enrollment, gubernatorial approval, and chaptering as Chapter 472 on September 9, 1987. Only the responsive page was OCRed; the remaining image-only pages are preserved but not searchable."
    },
    {
      "id": "gomes_v_mccsd_2019",
      "title": "Gomes v. Mendocino City Community Services District",
      "publisher": "California Court of Appeal, First Appellate District, Division Four",
      "document_date": "2019-05-14",
      "document_id": "A153078",
      "url": "https://www.courts.ca.gov/opinions/archive/A153078.PDF",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/historic-authority-recovery/gomes-v-mccsd-2019-a153078-ca-courts-official.pdf",
      "bytes": 305290,
      "sha256": "51a02e17fe55abb9f2fec83b8d382d4e650b4966a56cf5dc04d5bf0e830b2c7a",
      "note": "Published opinion, 35 Cal.App.5th 249, quoting AB 786 author Dan Hauser's signing letter and describing Ordinance 90-1. The court held Ordinance 07-1, Resolution 200, and Ordinance 07-4 void for failure to follow Water Code sections 10703-10706. The capture is the official California Courts PDF reached through the legacy opinions archive redirect."
    },
    {
      "id": "lafco_2025_annual_report",
      "title": "Mendocino LAFCo FY 2024-25 Annual Report",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2025-09",
      "url": "https://www.mendolafco.org/files/fe59d9b57/FY+2024-25+LAFCo+Annual+Report.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/lafco-recovery/2025-09-lafco-fy2024-25-annual-report.pdf",
      "bytes": 664827,
      "sha256": "9d3acbb5590b43040fd079afa01a1309d30b506a1c620c0ac315666e9148f22e",
      "note": "Published annual report. PDF page 5 lists FY2024-25 work-plan tasks and does not list MCCSD; page 8 reports aggregate MSR/SOI work-plan spending. It does not provide an agency-specific MCCSD expenditure."
    },
    {
      "id": "lafco_2025_07_07_packet",
      "title": "Mendocino LAFCo Commission Packet - July 7, 2025",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2025-07-07",
      "url": "https://www.mendolafco.org/files/495b63531/2025-07-07+Agenda+Packet+July+Regular+Meeting.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/lafco-recovery/2025-07-07-lafco-commission-packet-56133-policy.pdf",
      "bytes": 20317216,
      "sha256": "7152da4f26f18541d89e8a94b76bf412a14dfe22d61a20507fd254cbd3de04a2",
      "note": "PDF pages 42-44 reproduce LAFCo Policies 12.2.4 and 12.2.5 for regular and emergency outside-agency service. Page 45 contains the Executive Officer approval letter for Fort Bragg matter O-2025-02."
    },
    {
      "id": "lafco_2025_09_08_packet",
      "title": "Mendocino LAFCo Commission Packet - September 8, 2025",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2025-09-08",
      "url": "https://www.mendolafco.org/files/d103fbe2b/2025-09-08+Agenda+packet+September+Regular+Meeting.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/lafco-recovery/2025-09-08-lafco-commission-packet-fy-yearend.pdf",
      "bytes": 21099997,
      "sha256": "b891dc99aced536486226b1088a1129449f61d6e18819895f9af270f1e5c78ed",
      "note": "PDF pages 5-8 contain approved July 7 minutes for O-2025-02; page 11 contains active-project tracking; pages 85 and 88 reproduce the annual work-plan status and aggregate spending. MCCSD is absent from the public active docket and FY2024-25 task table."
    },
    {
      "id": "lafco_2025_11_03_packet",
      "title": "Mendocino LAFCo Commission Packet - November 3, 2025",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2025-11-03",
      "url": "https://www.mendolafco.org/files/d2e872757/2025-11-03+Agenda+Packet+November+Regular+Meeting.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/lafco-recovery/2025-11-03-lafco-commission-packet-oas-o-2025-04-new.pdf",
      "bytes": 19393408,
      "sha256": "6b619f767f86f38918c3b720562139f66a41ea3b20ae8cd573baef9be1f74bc8",
      "note": "PDF pages 40-41 present emergency sewer outside-agency service matter O-2025-04; pages 55-56 contain the Executive Officer approval letter."
    },
    {
      "id": "lafco_2025_12_01_packet",
      "title": "Mendocino LAFCo Commission Packet - December 1, 2025",
      "publisher": "Mendocino Local Agency Formation Commission",
      "document_date": "2025-12-01",
      "url": "https://www.mendolafco.org/files/d1b00e1eb/2025-12-01+Agenda+Packet+December+Regular+Meeting.pdf",
      "status": "captured",
      "capture_path": "captures/cases/UM_2025-0004/water-law/lafco-recovery/2025-12-01-lafco-commission-packet-oas-policy-12-2-5.pdf",
      "bytes": 3808873,
      "sha256": "529a2da423fbf9d9f4a56501c8577df6fa05f2e1d38b5a3ba2299860e9a5e2ef",
      "note": "PDF pages 5-8 contain approved November 3 minutes ratifying emergency OAS matter O-2025-04; pages 13-14 contain active-project tracking."
    }
  ],
  "open_questions": [
    "What is the number and text of the final signed UM_2025-0004 resolution?",
    "When was the UM_2025-0004 application submitted?",
    "Is County document 79036 identical to CEQAnet document 15?",
    "Why do records differ on site acreage and the number of existing wells?",
    "Which cited records are absent from the County's case packet?",
    "What action will the Planning Commission take when the continued hearing resumes September 3, 2026?"
  ],
  "questions": [
    {
      "id": "august-20-recent-conditions",
      "asked_at": "2026-08-20T23:37:06-07:00",
      "question": "What are the 20 recent conditions placed by County commissioners at the last meeting?",
      "status": "premise_corrected_partial_answer",
      "short_answer": "The Commission did not impose twenty new conditions on August 20. The existing December 2024 approval had twenty-one conditions. On August 20, staff and commissioners discussed several proposed revisions, including a newly numbered Special Condition 20, but unanimously continued the case to September 3 without approving the modification or adopting conditions.",
      "findings": [
        {
          "claim": "The August 20 action was a unanimous continuance to September 3, 2026.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:48:05-01:48:32",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "The December 2024 UM_2024-0008 approval was subject to twenty-one conditions, not twenty.",
          "source_id": "ccc_appeal_report",
          "pages": "3, 10",
          "confidence": "verified_from_official_report"
        },
        {
          "claim": "Staff's proposed Special Condition 20 would retain third-party certification of the hydrological study by Environmental Health before permit issuance, allowing that review to run in parallel with appeal periods.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "00:11:23-00:14:44",
          "confidence": "supported_by_recording"
        },
        {
          "claim": "Coastal Commission staff requested language more directly requiring the hydrological study review before issuance.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "00:11:29-00:11:56",
          "confidence": "supported_by_staff_presentation"
        },
        {
          "claim": "Commissioners also discussed Condition 14 (tributary restoration), tank-filling restrictions identified as Condition 16 in the current draft, emergency water language identified as Condition 17, drought monitoring, and preservation of an earlier pump-test condition.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "00:52:26-01:45:48",
          "confidence": "supported_by_recording_numbering_requires_document_check"
        }
      ],
      "unresolved": [
        "Obtain County documents 79046 and 79272 to compare the initial and revised resolutions line by line.",
        "Obtain the exact Coastal Commission proposed wording shown during the presentation.",
        "Reconcile the two provisions described during the hearing as Special Condition 20.",
        "Review the September 3 packet and action after that meeting occurs."
      ]
    },
    {
      "id": "coastal-groundwater-guideline-reference",
      "asked_at": "2026-08-22T08:29:03-07:00",
      "question": "What County groundwater guideline did the MUSD representative cite around 1:16 in the August 20 hearing, and what does it say?",
      "status": "answered_with_scope_limit",
      "short_answer": "GHD's Matt Kennedy cited the County of Mendocino Coastal Groundwater Development Guidelines, a Questa Engineering document dated July 1989 and marked as adopted by the Board of Supervisors on November 21, 1989. Its adjoining-well test treats pumping as an adverse effect if projected drawdown exceeds 10 percent of existing drawdown under maximum-day pumping conditions, or if adjoining well yield falls below 90 percent of that property's maximum-day demand. The guideline then requires mitigation. This technical threshold does not, by itself, decide whether MUSD may serve emergency water, what its DDW permit authorizes, or which later permit conditions govern the project.",
      "findings": [
        {
          "claim": "At approximately 01:15:47-01:16:29, Matt Kennedy read the adjoining-well criteria and named the County of Mendocino Coastal Groundwater Development Guidelines.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:15:47-01:16:29",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "The official guideline was prepared for Mendocino County Environmental Health by Questa Engineering Corporation, is dated July 1989, and is marked as adopted by the Board of Supervisors on November 21, 1989.",
          "source_id": "county_1989_coastal_groundwater_guidelines",
          "pages": 1,
          "confidence": "verified_from_official_record"
        },
        {
          "claim": "The guideline defines an adverse adjoining-well effect as more than 10 percent of existing drawdown under maximum-day pumping demand or a decline below 90 percent of maximum-day demand for the adjoining property, and states that mitigation is required if either occurs.",
          "source_id": "county_1989_coastal_groundwater_guidelines",
          "pages": 18,
          "confidence": "verified_from_official_record"
        }
      ],
      "unresolved": [
        "Determine how the 1989 guideline interacts with current County code, the certified LCP, and later MCCSD hydrological-study standards.",
        "Obtain Environmental Health's review of the 2025 MUSD hydrological study and any written application of the guideline to Test Well 7.",
        "Compare the 1989 County criterion with the different wording in MCCSD Ordinance 2020-01 before treating the standards as interchangeable."
      ]
    },
    {
      "id": "drought-trigger-authorities",
      "asked_at": "2026-08-22T08:41:00-07:00",
      "question": "How do Water Code section 13198(a) and MCCSD's Water Shortage Contingency Plan relate to the project's drought and overpumping conditions?",
      "status": "answered_with_authority_limit",
      "short_answer": "They are alternative event triggers, not a grant of water-service authority. Water Code §13198(a) defines a state drought scenario as a Governor's drought emergency or a State Water Board determination made through the specified notice and hearing process. The MCCSD plan uses local rainfall and indicator-well measurements to support Board declarations of Stages 1-4; Stage 3 brings mandatory conservation, a 20-percent allotment reduction, and possible moratoria on new extraction permits, drilling, and pump testing. The County permit tied emergency-water conditions to either §13198(a) or an MCCSD Stage 3 declaration. Neither trigger expands MUSD's DDW permit, proves authority to serve every parcel, or resolves who may receive hauled water.",
      "findings": [
        {
          "claim": "Water Code §13198(a) defines a drought scenario through either a Governor's drought emergency proclamation or a State Water Board determination following the specified notice and, where feasible, public-hearing process.",
          "source_id": "ca_water_code_13198_2026",
          "pages": 1,
          "confidence": "verified_from_current_official_code"
        },
        {
          "claim": "MCCSD's adopted plan uses rainfall and indicator-well levels to classify Stages 1-4.",
          "source_id": "mccsd_2020_water_shortage_plan",
          "pages": 18,
          "confidence": "verified_from_official_plan"
        },
        {
          "claim": "The plan's Stage 3 management response includes mandatory conservation and a 20-percent reduction in groundwater allotments.",
          "source_id": "mccsd_2020_water_shortage_plan",
          "pages": 22,
          "confidence": "verified_from_official_plan"
        },
        {
          "claim": "The County's approved project analysis describes Water Code §13198(a) and an MCCSD Stage 3 Emergency as alternative triggers for the emergency-water condition.",
          "source_id": "ccc_appeal_report",
          "pages": 27,
          "confidence": "verified_from_official_commission_report"
        }
      ],
      "unresolved": [
        "Obtain Resolution 2020-269 and any later amendments or replacements to establish the complete operative version history of the MCCSD plan.",
        "Obtain the operative November 26, 2025 DDW permit to determine what emergency withdrawal, filling, dispensing, customers, and service geography it authorizes.",
        "Determine whether either statutory or local drought trigger was formally in effect on any date when MUSD or MCCSD supplied project water."
      ]
    },
    {
      "id": "um2025-resolution-version-timeline",
      "asked_at": "2026-08-22T08:58:18-07:00",
      "question": "What did \"most recently posted resolution\" mean at the August 20 hearing, and what is the version timeline for UM_2025-0004?",
      "status": "answered_with_missing_version",
      "short_answer": "It referred to an August 18 revised draft, not an adopted resolution. The operative captured predecessor is signed Resolution PC 2024-0019, adopted December 19, 2024 with 21 conditions. County document 79046 is a captured August 2026 initial draft with 19 conditions. County document 79272 was posted August 18 and was treated at the hearing as the latest 20-condition draft, but its PDF has not been retrieved. The hearing itself demonstrates why numbering alone is unsafe: stream restoration was called Condition 14, displayed hydrological-review language was called proposed Condition 20, and the signed 2024 resolution had a different Condition 20 requiring seasonal pump testing. Staff also said Coastal Commission wording arrived after the latest draft was posted. The Commission continued the hearing without adopting any 2026 resolution, so PC 2024-0019 remains the captured adopted condition set.",
      "findings": [
        {
          "claim": "Signed Resolution PC 2024-0019 was adopted December 19, 2024 with 21 conditions; its Condition 20 requires pump testing during the MCCSD hydrological testing period.",
          "source_id": "county_pc_2024_0019",
          "pages": "5, 7",
          "confidence": "verified_from_signed_resolution"
        },
        {
          "claim": "County document 79046 is the captured August 2026 initial draft. Its conditions begin on page 4 and end with Condition 19 on page 6.",
          "source_id": "county_draft_resolution",
          "pages": "4, 6",
          "confidence": "verified_from_captured_draft"
        },
        {
          "claim": "Staff described proposed Condition 20 hydrological-review language as appearing in a memo posted Tuesday, then said Coastal Commission staff requested different wording after that posting.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "00:11:23-00:11:56",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "A commissioner said two resolutions were being tracked, requested tracked changes, and asked staff to ensure the correct resolution was ultimately adopted.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "00:51:22-00:52:25",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "During discussion, speakers distinguished the original resolution's pump-test Condition 20 from the new resolution and warned that adopting the new draft as then understood would lose that provision.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:23:39-01:24:07",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "Staff called the stream-restoration provision Condition 14 in the \"most recently posted resolution\" and said that posting omitted a Coastal Commission rewording request received after publication.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:27:33-01:27:55",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "The Planning Commission unanimously continued the matter to September 3, 2026 and adopted no 2026 resolution on August 20.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:48:05-01:48:32",
          "confidence": "verified_from_recording"
        }
      ],
      "unresolved": [
        "Obtain and hash County document 79272, the August 18 revised resolution, before treating its exact wording or numbering as verified.",
        "Obtain County document 79268, the Tuesday staff memo containing proposed Condition 20 language.",
        "Obtain a native redline or tracked-changes comparison between documents 79046 and 79272.",
        "Obtain every later draft and the final signed UM_2025-0004 resolution after the continued hearing."
      ]
    },
    {
      "id": "emergency-water-layered-authority",
      "asked_at": "2026-08-22T09:06:12-07:00",
      "question": "How do the Planning Commission's \"can\" or \"shall\" emergency-water condition, Water Board requirements, and LAFCo boundaries fit together?",
      "status": "answered_with_missing_operating_permit",
      "short_answer": "The agencies are regulating different acts, so the County condition cannot be read as the complete authority to supply water. The Planning Commission may limit a coastal permit and define when the approved project is eligible to dispense emergency water. Its adopted wording says water \"can\" be supplied; County counsel said changing that to \"shall\" could compel MUSD to dedicate its water to others without an impact analysis or MUSD's agreement. But either word remains a County land-use condition: it does not amend MUSD's drinking-water permit, grant MUSD general retail-water powers, or enlarge MCCSD's territory.\n\nThe State Water Board had already identified the overlap. DDW said the new sources and facilities required a domestic-water-supply permit amendment. The Board's funding staff separately asked for an emergency-delivery plan covering triggers, available volume, allocations, number of users, source water, and effects on neighboring wells, and said the funded scope did not match the environmental project. Those are not minor details; they are the operating questions the County's \"can\" condition does not answer. Because the November 26, 2025 DDW permit is still missing, the corpus cannot yet tell whether emergency dispensing, tanker filling, eligible customers, and geography were actually authorized or conditioned by DDW.\n\nLAFCo's records concern MCCSD, not an \"MUSD zone of influence.\" LAFCo confirmed MCCSD's active water and groundwater-management powers, but those powers are exercised within the District. Its 2020 review said MCCSD's sphere should be coterminous with its boundary and that, apart from wastewater service to Russian Gulch State Park, MCCSD provided no other out-of-agency services. By contrast, the County-created Emergency Water Service Area includes MCCSD plus an extension to the Slaughterhouse Gulch watershed. That County eligibility map is not an annexation, sphere amendment, DDW service area, or LAFCo approval.\n\nMUSD complicates the boundary question because it is a school district operating public-water system CA2300584, not MCCSD. The 2024 MOU says MUSD's source property is outside MCCSD's service area while MUSD distribution facilities extend into much of the village. The unresolved question is therefore not simply whether MCCSD crossed its boundary; it is what independent school-district authority and DDW permit terms allow MUSD to dispense water beyond its institutional users, and whether any MCCSD participation triggers LAFCo approval. No located public LAFCo record decides that project-specific question.",
      "findings": [
        {
          "claim": "Adopted Condition 18 says stored water \"can be supplied\" by MUSD during specified drought conditions, subject to the Emergency Water Service Area, a 315,000-gallon reserve, and a 40,000-gallon daily cap.",
          "source_id": "county_pc_2024_0019",
          "pages": 7,
          "confidence": "verified_from_signed_resolution"
        },
        {
          "claim": "County counsel said \"can\" had appeared since the initial draft and in the 2024 adoption; changing it to \"shall\" raised concern that the County would require MUSD to dedicate its water to others without impact analysis or MUSD agreement.",
          "source_id": "hearing_video_2026_08_20",
          "timestamp": "01:10:03-01:10:49",
          "confidence": "verified_from_recording"
        },
        {
          "claim": "The State Water Board said MUSD needed a DDW domestic-water-supply permit amendment for the new or modified sources and system components.",
          "source_id": "ddw_dfa_2023_comment_letter",
          "pages": 1,
          "confidence": "verified_from_official_agency_letter"
        },
        {
          "claim": "Water Board funding staff said the financing scope and environmental project did not match and requested an emergency-delivery plan covering triggers, volume, allocation, users, sources, and neighboring-well effects.",
          "source_id": "ddw_dfa_2023_comment_letter",
          "pages": 2,
          "confidence": "verified_from_official_agency_letter"
        },
        {
          "claim": "LAFCo confirmed MCCSD's active water and groundwater-management powers, including beneficial-use water service and the Water Code groundwater program.",
          "source_id": "lafco_2022_groundwater_authority",
          "pages": 1,
          "confidence": "verified_from_official_lafco_letter"
        },
        {
          "claim": "LAFCo's 2020 review reported that MCCSD provided no out-of-agency service other than wastewater treatment for Russian Gulch State Park and recommended a sphere coterminous with the District boundary.",
          "source_id": "mccsd_2020_msr_soi",
          "pages": "63, 68",
          "confidence": "verified_from_adopted_msr_soi_record"
        },
        {
          "claim": "The County emergency-water condition extended eligibility beyond the MCCSD boundary to the Slaughterhouse Gulch watershed; the Coastal Commission staff treated that as the County's defined permit area.",
          "source_id": "ccc_appeal_report",
          "pages": 27,
          "confidence": "verified_from_official_commission_report"
        },
        {
          "claim": "The 2024 MOU says MUSD water-system assets on Little Lake Road are outside MCCSD's service area while MUSD distribution extends into the village and through much of the MCCSD service area; it limits non-MUSD/non-fire access to declared drought emergencies.",
          "source_id": "mccsd_musd_2024_mou",
          "pages": "2, 3",
          "confidence": "verified_from_executed_mou"
        }
      ],
      "unresolved": [
        "Obtain the operative November 26, 2025 DDW permit and incorporated operating conditions for CA2300584.",
        "Obtain DDW's approved emergency-distribution, tanker-filling, customer-eligibility, and service-geography records.",
        "Obtain any project-specific LAFCo advice, pre-application review, or determination concerning MCCSD participation or out-of-area service.",
        "Determine the school-district authority MUSD relies on to provide potable water to non-MUSD users."
      ]
    }
  ],
  "waterLaw": {
    "schema_version": 1,
    "system": {
      "id": "CA2300584",
      "name": "Mendocino School District - Mendocino",
      "operator": "Mendocino Unified School District",
      "regulator": "State Water Resources Control Board, Division of Drinking Water",
      "classification": "nontransient_noncommunity",
      "status": "active",
      "source_type": "groundwater",
      "population_nontransient": 579,
      "connections": 15,
      "registry_url": "https://sdwis.waterboards.ca.gov/PDWW/JSP/WaterSystemDetail.jsp?tinwsys_is_number=2882&tinwsys_st_code=CA",
      "caveat": "The public registry describes a school system but does not establish a parcel-level service territory or the terms of its November 2025 permit amendment."
    },
    "lcp_findings": [
      {
        "id": "mccsd_extraction_rules_not_incorporated",
        "finding": "The County never applied for an LCP amendment incorporating MCCSD groundwater-management extraction-permit provisions into the certified Mendocino Town LCP.",
        "source_id": "ccc_2017_town_lcp_report",
        "locator": "PDF page 82",
        "qualification": "The certified LCP still contains its own groundwater rules and uses some MCCSD determinations and demand standards. Operational reliance on an MCCSD permit does not incorporate the entire District ordinance.",
        "practice_source_ids": [
          "nextrequest_22_583_mccsd_2018_letter",
          "nextrequest_22_583_mccsd_2019_comment",
          "nextrequest_22_583_mccsd_drought_email",
          "nextrequest_22_583_mccsd_2022_letter"
        ]
      }
    ],
    "boundaries": [
      {
        "id": "musd_ddw_service_description",
        "name": "MUSD permitted public-water-system service",
        "kind": "ddw_service_description",
        "status": "verified_2021_geometry_exact_legal_scope_unknown",
        "authority": "State Water Resources Control Board, Division of Drinking Water",
        "description": "Existing institutional users and any emergency dispensing authorized by the domestic water supply permit. The operative permit is not yet in the corpus.",
        "source_ids": [
          "ddw_2021_service_area",
          "ceqanet_water_supply_amendment"
        ]
      },
      {
        "id": "mccsd_boundary",
        "name": "MCCSD jurisdictional boundary",
        "kind": "district_boundary",
        "status": "verified_general_description",
        "authority": "Mendocino LAFCo",
        "description": "Approximately one square mile between Slaughterhouse Gulch and Big River. This is the territory in which MCCSD exercises its activated powers.",
        "source_ids": [
          "mccsd_2020_msr_soi",
          "lafco_2020_resolution_2020_21_01",
          "county_2026_mccsd_boundary"
        ]
      },
      {
        "id": "mccsd_soi",
        "name": "MCCSD sphere of influence",
        "kind": "lafco_sphere",
        "status": "coterminous_with_district",
        "authority": "Mendocino LAFCo",
        "source_ids": [
          "mccsd_2020_msr_soi",
          "lafco_2020_resolution_2020_21_01"
        ]
      },
      {
        "id": "county_emergency_drought_area",
        "name": "County emergency drought water service area",
        "kind": "county_permit_eligibility_area",
        "status": "published_map_verified_native_gis_and_parcel_intersections_needed",
        "authority": "Mendocino County Planning Commission permit condition",
        "description": "MCCSD territory plus an extension to the Slaughterhouse Gulch watershed boundary, selected during December 2024 permit deliberations. This has not been shown to be a DDW service territory, district annexation, sphere amendment, or LAFCo-approved out-of-area service area.",
        "source_ids": [
          "ccc_appeal_report",
          "county_exhibit_i"
        ]
      },
      {
        "id": "grant_beneficiary_area",
        "name": "State grant beneficiary area",
        "kind": "funding_scope",
        "status": "2023_agreements_verified_later_amendments_needed",
        "authority": "Department of Water Resources / State Water Resources Control Board",
        "description": "DWR Amendment 1 funds emergency storage for eligible customers and uses community-wide design assumptions, but does not supply a parcel-level beneficiary polygon. The County's later Slaughterhouse Gulch eligibility area has not been tied to a DWR or DFA amendment.",
        "source_ids": [
          "musd_2023_final_subsequent_mnd",
          "musd_2023_response_and_funding_agreements"
        ]
      },
      {
        "id": "practical_delivery_area",
        "name": "Practical tanker delivery area",
        "kind": "operational_area",
        "status": "operating_plan_needed",
        "authority": "MUSD / MCCSD / licensed water hauler",
        "description": "Locations to which water could actually be hauled and discharged. It may differ from every legal or funding boundary above.",
        "source_ids": [
          "nextrequest_2021_hauled_water"
        ]
      }
    ],
    "authorities": [
      {
        "id": "wat_13198",
        "citation": "California Water Code § 13198",
        "title": "Drought-scenario and interim-relief definitions",
        "topic": "drought_trigger",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=13198.&lawCode=WAT",
        "effect": "Defines a drought scenario and lists forms of interim relief, including hauled water, community tanks, emergency interties, wells, and permanent connections.",
        "does_not_establish": "It does not enlarge MUSD's drinking-water permit or MCCSD's boundary and does not independently authorize retail service."
      },
      {
        "id": "wat_13194",
        "citation": "California Water Code § 13194",
        "title": "Funding for immediate drinking-water relief",
        "topic": "emergency_funding",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=13194.&lawCode=WAT",
        "effect": "Allows State Board funding for tanks, hauled water, or bottled water for households whose wells fail through drought, wildfire, or disaster.",
        "does_not_establish": "Territorial operating authority."
      },
      {
        "id": "wat_10700_10717",
        "citation": "California Water Code §§ 10700–10717",
        "title": "Mendocino-specific groundwater management authority",
        "topic": "groundwater_management",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=6.&chapter=&part=2.7.&lawCode=WAT",
        "effect": "Applies only within MCCSD's existing boundaries; authorizes eligible local agencies to establish groundwater programs, enter joint-powers agreements for that purpose, regulate extraction, and exercise specified replenishment-district powers.",
        "does_not_establish": "It does not itself create a municipal central water system. Section 10717 ends these special powers when such a system is completed and implemented to supply inhabitants within the local agency."
      },
      {
        "id": "gomes_v_mccsd_2019",
        "citation": "Gomes v. Mendocino City Community Services District (2019) 35 Cal.App.5th 249",
        "title": "Judicial interpretation of MCCSD groundwater-program procedures",
        "topic": "groundwater_management",
        "url": "https://www.courts.ca.gov/opinions/archive/A153078.PDF",
        "effect": "Quotes the AB 786 author's signing letter, describes Ordinance 90-1, and holds that Ordinance 07-1, Resolution 200, and Ordinance 07-4 were void because MCCSD did not follow Water Code sections 10703-10706 when adopting and implementing the groundwater management program.",
        "does_not_establish": "The opinion does not reproduce the complete signed Ordinance 90-1 or its amendments and does not adjudicate MUSD's current drinking-water authority."
      },
      {
        "id": "hsc_116525",
        "citation": "California Health and Safety Code § 116525",
        "title": "Public water system operating permit",
        "topic": "drinking_water_permit",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=116525.&lawCode=HSC",
        "effect": "Requires a permit to operate a public water system and permits the State Board to revise it."
      },
      {
        "id": "hsc_116550",
        "citation": "California Health and Safety Code § 116550",
        "title": "Changes requiring an amended permit",
        "topic": "drinking_water_permit",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=116550.&lawCode=HSC",
        "effect": "Restricts changes to source, treatment, or the permitted distribution system without an amended permit, subject to the statutory exceptions."
      },
      {
        "id": "hsc_116555",
        "citation": "California Health and Safety Code § 116555",
        "title": "Public water system duties",
        "topic": "drinking_water_operations",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=116555.&lawCode=HSC",
        "effect": "Requires reliable, adequate, potable supply, compliance with standards, backflow protection, and appropriately certified operators."
      },
      {
        "id": "hsc_116682",
        "citation": "California Health and Safety Code § 116682",
        "title": "Consolidation and extension of service",
        "topic": "consolidation",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=104.&chapter=4.&part=12.&lawCode=HSC",
        "effect": "Authorizes State Board consolidation or service-extension orders after a defined process for specified failing or at-risk systems and domestic wells.",
        "does_not_establish": "No located record shows that the State Board invoked this authority here."
      },
      {
        "id": "gov_56133",
        "citation": "California Government Code § 56133",
        "title": "Service outside a city or district boundary",
        "topic": "lafco_out_of_area_service",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=56133.&lawCode=GOV",
        "effect": "Generally requires LAFCo's prior written approval for a city or district to provide new or extended service outside its boundary.",
        "does_not_establish": "The Cortese-Knox-Hertzberg definition of district excludes school districts, so this section governs an MCCSD extension but does not answer MUSD's authority."
      },
      {
        "id": "gov_61100_a",
        "citation": "California Government Code § 61100(a)",
        "title": "Community services district water power",
        "topic": "district_power",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=61100.&lawCode=GOV",
        "effect": "Allows a community services district to supply water within its boundaries."
      },
      {
        "id": "gov_6500",
        "citation": "California Government Code §§ 6500–6509.7",
        "title": "Joint Exercise of Powers Act",
        "topic": "joint_powers",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=7.&chapter=5.&part=&lawCode=GOV&title=1.",
        "effect": "Allows public agencies, with governing-body authorization, to jointly exercise powers common to the contracting parties and optionally create a separate administering entity.",
        "does_not_establish": "It does not manufacture a power that is not common to the parties or replace independent DDW, LAFCo, land-use, or funding approvals."
      },
      {
        "id": "hsc_116275",
        "citation": "California Health and Safety Code § 116275",
        "title": "Public water system definitions",
        "topic": "drinking_water_classification",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=116275",
        "effect": "Defines public water systems and community and noncommunity classifications based on water provision, connections, population, and patterns of use.",
        "does_not_establish": "Public-water-system status is not necessarily public ownership and does not itself grant a local government general water-service powers."
      },
      {
        "id": "gov_56824",
        "citation": "California Government Code §§ 56824.10-56824.14",
        "title": "Activation of latent district powers",
        "topic": "lafco_activation",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=56824.10&lawCode=GOV",
        "effect": "Requires district and LAFCo hearings, a service plan, financing information, and LAFCo approval to activate a latent or new class of service."
      },
      {
        "id": "edc_35160",
        "citation": "California Education Code §§ 35160-35160.1",
        "title": "School district general powers",
        "topic": "school_district_power",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=35160.&lawCode=EDC",
        "effect": "Gives school districts broad authority for activities consistent with law and school-district purposes.",
        "does_not_establish": "It does not expressly answer whether MUSD may act as a continuing area-wide retail water supplier."
      },
      {
        "id": "prc_30600",
        "citation": "California Public Resources Code § 30600(a)",
        "title": "Coastal permit is additional to other permits",
        "topic": "coastal_permit_scope",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=30600.&lawCode=PRC",
        "effect": "Makes the coastal development permit an additional approval rather than a substitute for drinking-water, district, or other legal authority."
      }
    ],
    "institutional_roles": [
      {
        "actor": "Mendocino County Planning Commission",
        "can_authorize": "Coastal development permit, physical development, and LCP-related conditions.",
        "cannot_establish_alone": "DDW operating authority, school-district powers, or an MCCSD boundary."
      },
      {
        "actor": "MUSD",
        "can_authorize": "Project implementation within its lawful powers and DDW permit.",
        "cannot_establish_alone": "An expanded statutory or DDW service territory."
      },
      {
        "actor": "State Water Resources Control Board, Division of Drinking Water",
        "can_authorize": "Sources, treatment, storage, distribution, operators, and public-water-system permit conditions.",
        "cannot_establish_alone": "County zoning or an MCCSD annexation."
      },
      {
        "actor": "MCCSD",
        "can_authorize": "Activated district services within its boundary and drought-stage declarations.",
        "cannot_establish_alone": "A latent central-water service or out-of-boundary service."
      },
      {
        "actor": "Mendocino LAFCo",
        "can_authorize": "MCCSD sphere changes, annexation, latent powers, and applicable out-of-area service.",
        "cannot_establish_alone": "MUSD's DDW permit or County coastal approval."
      },
      {
        "actor": "California Coastal Commission",
        "can_authorize": "Appeal decisions under the certified LCP and Coastal Act.",
        "cannot_establish_alone": "Drinking-water operating authority or groundwater rights."
      }
    ],
    "priority_missing_records": [
      {
        "id": "ddw_2025_amended_permit",
        "title": "CA2300584 amended domestic water supply permit issued November 26, 2025",
        "why": "Determines whether DDW reviewed and authorized emergency dispensing, customers, tanker filling, service scope, sources, storage, and operating conditions."
      },
      {
        "id": "ddw_preproject_permit",
        "title": "Immediately preceding CA2300584 permit and amendments",
        "why": "Establishes the baseline system, customers, facilities, and service description."
      },
      {
        "id": "county_exhibit_i",
        "title": "Native Exhibit I GIS package and parcel-intersection list",
        "why": "The published PDF is captured, but it lacks parcel boundaries. Native GIS is needed to reproduce the polygon and identify wholly or partly intersected parcels."
      },
      {
        "id": "dwr_4600014624",
        "title": "DWR Agreement 4600014624 amendments after Amendment 1",
        "why": "The March 2026 DWR letter proves a later amendment exists. It may revise scope, deadlines, ownership, operating duties, or beneficiary provisions."
      },
      {
        "id": "state_revolving_fund_agreement",
        "title": "D2202005 amendments and MUSD funding-project update",
        "why": "The original agreement is captured, but the State Board said its scope did not match the expanded project. A 2026 status report also gives a completion date different from the executed original."
      },
      {
        "id": "lafco_project_correspondence",
        "title": "Any LAFCo determination or correspondence concerning the MUSD/MCCSD project",
        "why": "Shows whether district powers, annexation, or out-of-area service were considered."
      },
      {
        "id": "measure_a_canvass",
        "title": "Certified November 5, 1985 Measure A ballot and canvass",
        "why": "Later official records report a 141-76 vote, but the contemporaneous certified election record is not publicly available in the repositories searched."
      },
      {
        "id": "early_mccsd_groundwater_ordinances",
        "title": "Signed Ordinance 90-1 and amendments 91-3, 92-2, 00-1, 01-1, and 04-1",
        "why": "Later ordinances and Gomes describe this legislative lineage, but they do not substitute for the original enacted texts and amendment history."
      },
      {
        "id": "ab786_bill_file",
        "title": "Complete 1987 AB 786 bill and chaptering file",
        "why": "The Assembly Final History proves procedural dates and votes. Bill versions, committee analyses, author correspondence, and the Governor's chaptering file remain necessary to reconstruct legislative intent."
      }
    ]
  },
  "authorityChain": {
    "schema_version": 1,
    "question": "How do the State Water Board, MUSD, MCCSD, LAFCo, County, and their agreements combine—and not combine—to authorize groundwater management, a public water system, and emergency community water delivery?",
    "preliminary_conclusion": "The project is presently a layered cooperation model, not a demonstrated transfer or merger of powers. MCCSD regulates groundwater and holds active CSD water powers; MUSD owns and operates CA2300584; DDW regulates that public water system; LAFCo controls applicable MCCSD boundary and service-class questions; and the County controls land-use and coastal permits. The 2024 MOU allocates project, asset, grant, and operating responsibilities but does not on its face create a separate joint-powers entity or supply missing statutory authority.",
    "actors": [
      {
        "id": "swrcb_ddw",
        "name": "State Water Resources Control Board — Division of Drinking Water",
        "role": "public_water_system_regulator",
        "powers": [
          "Issue and amend the domestic water supply permit for CA2300584.",
          "Regulate source, treatment, storage, distribution, water quality, operators, and reliability.",
          "Review technical, managerial, and financial capacity."
        ],
        "limits": [
          "Does not activate MCCSD services or alter MCCSD boundaries.",
          "A DDW permit regulates operation; it does not itself create MUSD's underlying local-government power."
        ],
        "source_ids": [
          "ca_drinking_water_lawbook_2026",
          "ddw_public_water_system_guide",
          "ddw_permit_application",
          "ddw_amended_permit_application"
        ]
      },
      {
        "id": "swrcb_dfa",
        "name": "State Water Resources Control Board — Division of Financial Assistance",
        "role": "financing_agency",
        "powers": [
          "Administer DWSRF agreement D2202005 and approve material funded-project changes."
        ],
        "limits": [
          "Financing approval is not a drinking-water operating permit or LAFCo service authorization."
        ],
        "source_ids": [
          "musd_2023_response_and_funding_agreements",
          "ddw_dfa_2023_comment_letter"
        ]
      },
      {
        "id": "dwr",
        "name": "California Department of Water Resources",
        "role": "grant_agency",
        "powers": [
          "Administer Agreement 4600014624 and approve material UMBDR project changes."
        ],
        "limits": [
          "Grant eligibility and scope do not establish public-water-system or district authority."
        ],
        "source_ids": [
          "musd_2023_response_and_funding_agreements",
          "musd_2026_project_status"
        ]
      },
      {
        "id": "rwqcb",
        "name": "North Coast Regional Water Quality Control Board",
        "role": "recycled_water_and_discharge_regulator",
        "powers": [
          "Regulate wastewater discharge and recycled-water production and use."
        ],
        "limits": [
          "Does not issue the domestic water supply permit for CA2300584."
        ],
        "source_ids": [
          "mccsd_2020_msr_soi"
        ]
      },
      {
        "id": "musd",
        "name": "Mendocino Unified School District",
        "role": "public_water_system_owner_operator",
        "powers": [
          "Own and operate CA2300584 subject to its DDW permit.",
          "Exercise school-district powers consistent with law and school purposes.",
          "Own the combined project's water-system assets under the 2024 MOU."
        ],
        "limits": [
          "Public-water-system status is a regulatory classification, not proof of general area-wide retail-water power.",
          "The operative DDW permit is needed to establish authorized emergency dispensing and customers."
        ],
        "source_ids": [
          "mccsd_musd_2024_mou",
          "ca_drinking_water_lawbook_2026"
        ]
      },
      {
        "id": "mccsd",
        "name": "Mendocino City Community Services District",
        "role": "groundwater_manager_and_csd_with_water_powers",
        "powers": [
          "Supply water for beneficial uses within its boundary under Government Code §61100(a).",
          "Administer the special Water Code §§10700–10717 groundwater program.",
          "Require extraction permits, studies, meters, allotments, and drought reductions.",
          "Continue and expand pre-2006 classes of active water service identified by LAFCo."
        ],
        "limits": [
          "A municipal central water system and certain replenishment activities were identified by LAFCo as new or different service classes requiring activation.",
          "Water Code §10717 terminates the special Part 2.7 powers when a municipal central system is completed and implemented for inhabitants within MCCSD.",
          "Its ordinances were not incorporated wholesale into the certified Town LCP."
        ],
        "source_ids": [
          "mccsd_water_code_10700_10717",
          "mccsd_ordinance_2020_01",
          "lafco_2005_csd_powers",
          "lafco_2022_groundwater_authority",
          "mccsd_2020_msr_soi",
          "ccc_2017_town_lcp_report"
        ]
      },
      {
        "id": "lafco",
        "name": "Mendocino Local Agency Formation Commission",
        "role": "district_boundary_and_service_class_regulator",
        "powers": [
          "Determine MCCSD active and latent classes of service.",
          "Approve applicable service activation, sphere changes, annexation, and out-of-area district service."
        ],
        "limits": [
          "Does not issue a DDW operating permit or confer school-district powers."
        ],
        "source_ids": [
          "lafco_2005_csd_powers",
          "lafco_2022_groundwater_authority",
          "mccsd_2020_msr_soi",
          "lafco_2020_resolution_2020_21_01",
          "lafco_2025_07_07_packet",
          "lafco_2025_09_08_packet",
          "lafco_2025_12_01_packet"
        ]
      },
      {
        "id": "county",
        "name": "Mendocino County",
        "role": "land_use_coastal_and_well_permitting",
        "powers": [
          "Issue County permits and impose legally supportable project conditions.",
          "Apply the certified LCP's groundwater and proof-of-water provisions."
        ],
        "limits": [
          "Cannot substitute a County permit for DDW, LAFCo, or independent agency authority.",
          "Operational reliance on an MCCSD permit does not incorporate the entire MCCSD ordinance into the LCP."
        ],
        "source_ids": [
          "ccc_2017_town_lcp_report",
          "nextrequest_22_583_mccsd_drought_email"
        ]
      }
    ],
    "instruments": [
      {
        "id": "water_code_part_2_7",
        "title": "Water Code §§10700–10717",
        "kind": "special_groundwater_statute",
        "effect": "Applies only within MCCSD's existing boundaries; authorizes an eligible local agency to adopt a groundwater program, enter a JPA for that purpose, regulate extraction, and exercise replenishment-district powers.",
        "limits": "Requires specified adoption procedures and agreements before acting within another water agency's boundaries. Section 10717 contains a central-system termination trigger.",
        "source_ids": [
          "mccsd_water_code_10700_10717",
          "mccsd_2012_groundwater_management_plan",
          "ca_assembly_final_history_1987_88",
          "gomes_v_mccsd_2019"
        ]
      },
      {
        "id": "county_mccsd_1990_transfer",
        "title": "County-MCCSD Agreement 90-113",
        "kind": "interagency_groundwater_agreement",
        "effect": "Transfers County groundwater-extraction regulation within MCCSD to the District to the extent authorized by law, while retaining County well construction standards and specified permit enforcement.",
        "limits": "It is not a transfer of all County land-use authority, a drinking-water operating permit, or authority outside MCCSD's boundary.",
        "source_ids": [
          "mccsd_2012_groundwater_management_plan"
        ]
      },
      {
        "id": "csd_water_power",
        "title": "Government Code §61100(a) and Measure A",
        "kind": "underlying_district_power",
        "effect": "Authorizes MCCSD to supply water for beneficial uses within its boundary in the same manner as a municipal water district.",
        "limits": "Particular new or different classes of service may still require LAFCo activation; boundaries and other regulatory permits remain controlling.",
        "source_ids": [
          "lafco_2005_csd_powers",
          "lafco_2022_groundwater_authority",
          "mccsd_2020_msr_soi"
        ]
      },
      {
        "id": "joint_exercise_of_powers_act",
        "title": "Government Code §§6500 et seq.",
        "kind": "cooperation_authority",
        "effect": "Permits public agencies, with governing-body authorization, to jointly exercise a power common to the contracting parties. An agreement must identify the purpose or power and the method of exercise.",
        "limits": "A JPA cannot manufacture a power that is not common to the parties. Additional filing, treasury, accountability, and audit rules apply, especially when a separate entity is created.",
        "source_ids": [
          "state_controller_jpa_guide",
          "mccsd_water_code_10700_10717"
        ]
      },
      {
        "id": "mou_2024",
        "title": "2024 MUSD–MCCSD Memorandum of Understanding",
        "kind": "cooperative_project_agreement",
        "effect": "Combines funded construction into one project; assigns MUSD ownership, operation, CEQA, and school-system responsibilities; preserves MCCSD and MUSD control over their respective grant-funded changes; and limits non-MUSD/non-fire access to declared drought emergencies when neighboring districts cannot provide hauled water, through a future application process.",
        "limits": "It creates no separate entity, identifies no JPA governance or common power, and does not amend the DDW permit or LAFCo approvals. Its legal status as a non-entity joint-powers agreement is not established by the current record; substance and governing-body authorization, not the document's title, would control.",
        "source_ids": [
          "mccsd_musd_2024_mou",
          "mccsd_2024_11_25_board_minutes",
          "mccsd_2024_11_25_board_packet",
          "musd_2024_11_21_board_minutes",
          "musd_2024_11_21_board_packet"
        ]
      },
      {
        "id": "mou_2022",
        "title": "2022 MUSD-MCCSD Water Supply and Storage Project MOU",
        "kind": "superseded_cooperative_project_agreement",
        "effect": "Proposed MCCSD ownership and operation of a new 500,000-gallon tank and new wells, with MCCSD providing emergency water to eligible residential and commercial customers.",
        "limits": "The recovered instrument is an unsigned packet copy. Both boards approved the agreement, but the signed original remains missing, and the agreement was replaced in April 2023.",
        "source_ids": [
          "mccsd_2022_08_29_board_minutes",
          "musd_2022_09_08_board_minutes",
          "musd_2022_09_08_board_packet",
          "mccsd_2022_10_03_board_minutes"
        ]
      },
      {
        "id": "mou_2023",
        "title": "April 20, 2023 MUSD-MCCSD Memorandum of Understanding",
        "kind": "superseded_cooperative_project_agreement",
        "effect": "Combined the agencies' potable well and storage projects and divided access, operating, maintenance, grant, and asset responsibilities.",
        "limits": "MCCSD rescinded this agreement November 25, 2024. It must not be treated as the current agreement or confused with the separate 1997 recycled-water MOU.",
        "source_ids": [
          "mccsd_musd_2023_mou",
          "mccsd_2023_04_19_board_minutes",
          "mccsd_2023_04_19_board_packet",
          "musd_2023_04_20_board_minutes",
          "musd_2023_04_20_board_packet",
          "mccsd_2024_11_25_board_minutes"
        ]
      },
      {
        "id": "gomes_2019",
        "title": "Gomes v. Mendocino City Community Services District (2019) 35 Cal.App.5th 249",
        "kind": "published_judicial_interpretation",
        "effect": "Holds that the special Water Code provisions authorize groundwater extraction limits but require the statutory adoption process for new or materially expanded groundwater-management programs.",
        "limits": "The decision invalidated Ordinance 07-1, Resolution 200, and Ordinance 07-4 without prejudice to lawful readoption; it does not invalidate Ordinance 90-1 or determine potable-project service authority.",
        "source_ids": [
          "gomes_v_mccsd_2019"
        ]
      },
      {
        "id": "lafco_policy_12_2_5",
        "title": "Mendocino LAFCo Policy 12.2.5",
        "kind": "emergency_outside_agency_service_procedure",
        "effect": "Implements Government Code section 56133(d) by allowing the Executive Officer to administratively approve urgent public-health or safety outside-agency service, followed by Commission ratification.",
        "limits": "It applies to a city or LAFCo-defined district requesting outside service. Government Code section 56036 excludes school districts, so the policy does not by itself govern MUSD acting in its own capacity.",
        "source_ids": [
          "lafco_2025_07_07_packet",
          "lafco_2025_11_03_packet",
          "lafco_2025_12_01_packet"
        ]
      },
      {
        "id": "recycled_water_mou_1997",
        "title": "1997 MUSD-MCCSD Recycled-Water MOU and Joint Resolution 97-1",
        "kind": "recycled_water_cooperation_agreement",
        "effect": "Commits both districts to the capital and operating arrangements for tertiary recycled water used to irrigate MUSD athletic fields.",
        "limits": "It concerns recycled irrigation water under separate water-quality regulation, not the present potable emergency-water project.",
        "source_ids": [
          "mccsd_2012_groundwater_management_plan"
        ]
      },
      {
        "id": "ddw_permit",
        "title": "CA2300584 domestic water supply permit",
        "kind": "regulatory_operating_instrument",
        "effect": "Regulates MUSD's operation of the public water system.",
        "limits": "The November 26, 2025 amended permit is missing, so its treatment of community emergency distribution, tanker filling, and service scope remains unknown.",
        "source_ids": [
          "ceqanet_water_supply_amendment"
        ]
      }
    ],
    "relationships": [
      {
        "id": "mccsd_to_musd_groundwater",
        "from_actor": "mccsd",
        "to_actor": "musd",
        "relationship": "groundwater_regulation_of_project_wells",
        "analysis": "The MOU subjects project test wells to Ordinance 2020-01. That is MCCSD exercising its groundwater program, not operating MUSD's public water system.",
        "source_ids": [
          "mccsd_musd_2024_mou",
          "mccsd_ordinance_2020_01"
        ]
      },
      {
        "id": "ddw_to_musd",
        "from_actor": "swrcb_ddw",
        "to_actor": "musd",
        "relationship": "permit_and_public_health_regulation",
        "analysis": "DDW controls whether and how CA2300584 may use new sources, treatment, storage, distribution, and emergency dispensing.",
        "source_ids": [
          "ca_drinking_water_lawbook_2026",
          "ceqanet_water_supply_amendment"
        ]
      },
      {
        "id": "mccsd_musd_mou",
        "from_actor": "mccsd",
        "to_actor": "musd",
        "relationship": "cooperative_implementation",
        "analysis": "The agencies pool project execution and funding but retain separate legal identities, approvals, grant control, and regulatory responsibilities.",
        "source_ids": [
          "mccsd_musd_2024_mou",
          "mccsd_2024_11_25_board_minutes",
          "musd_2024_11_21_board_minutes"
        ]
      },
      {
        "id": "county_to_mccsd_groundwater",
        "from_actor": "county",
        "to_actor": "mccsd",
        "relationship": "agreed_transition_of_groundwater_extraction_regulation",
        "analysis": "Agreement 90-113 transferred groundwater-extraction regulation within MCCSD to the District to the extent authorized by law, while the County retained well-construction standards and specified permit enforcement.",
        "source_ids": [
          "mccsd_2012_groundwater_management_plan"
        ]
      },
      {
        "id": "musd_mccsd_recycled_water_1997",
        "from_actor": "mccsd",
        "to_actor": "musd",
        "relationship": "recycled_water_project_cooperation",
        "analysis": "The 1997 MOU and Joint Resolution 97-1 are a prior model of cooperation, but their subject is tertiary recycled water for athletic-field irrigation, not potable emergency supply.",
        "source_ids": [
          "mccsd_2012_groundwater_management_plan"
        ]
      },
      {
        "id": "lafco_to_mccsd",
        "from_actor": "lafco",
        "to_actor": "mccsd",
        "relationship": "service_class_and_boundary_oversight",
        "analysis": "LAFCo confirmed active groundwater and limited water powers but found a municipal central system to be a new or different class requiring activation.",
        "source_ids": [
          "mccsd_2020_msr_soi",
          "lafco_2022_groundwater_authority"
        ]
      },
      {
        "id": "county_to_project",
        "from_actor": "county",
        "to_actor": "musd",
        "relationship": "coastal_and_land_use_permitting",
        "analysis": "County approval authorizes development under land-use law; it does not itself authorize MUSD's water-system operation or MCCSD service expansion.",
        "source_ids": [
          "county_pc_2024_0019"
        ]
      }
    ],
    "decision_chain": [
      {
        "step": 1,
        "question": "What physical or governmental act is proposed?",
        "why": "Aquifer regulation, well construction, public-system operation, emergency dispensing, hauled-water eligibility, and central retail service are different acts."
      },
      {
        "step": 2,
        "question": "Which agency possesses that power independently?",
        "why": "A contract or JPA coordinates existing powers; it does not substitute for the underlying enabling statute."
      },
      {
        "step": 3,
        "question": "Where and for whom will the power be exercised?",
        "why": "MCCSD boundary, MUSD's permitted operation, the County EWSA, grant scope, and practical hauling area are not interchangeable."
      },
      {
        "step": 4,
        "question": "Is the agreement a service contract, cooperative MOU, non-entity JPA, or separate-entity JPA?",
        "why": "The classification determines common-power, authorization, filing, governance, treasury, audit, liability, and records requirements."
      },
      {
        "step": 5,
        "question": "Which independent approvals remain necessary?",
        "why": "DDW, LAFCo, County/Coastal, grantor, and water-quality approvals do different work."
      },
      {
        "step": 6,
        "question": "Does Water Code §10717's municipal-central-system trigger apply?",
        "why": "If triggered, the special groundwater powers in Part 2.7 end, although MCCSD's other statutory water powers do not necessarily disappear."
      }
    ],
    "unresolved": [
      "The operative November 26, 2025 DDW permit and its authorized service description.",
      "Whether either agency treated the approved 2024 MOU as a Government Code §6500 agreement.",
      "The asserted power common to MUSD and MCCSD if the MOU is claimed to be a JPA.",
      "Whether emergency hauled supply can become a municipal central system for §10717 purposes.",
      "Any nonpublic LAFCo advice or pre-application consultation specific to the MUSD/MCCSD potable-water project after 2022; none appears in the public docket searched through July 2026.",
      "The certified 1985 Measure A election record, complete AB 786 legislative history, and original Ordinance 90-1."
    ]
  }
};
