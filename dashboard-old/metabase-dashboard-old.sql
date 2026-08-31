--Рост числа образцов по годам
SELECT 
    YEAR(created) AS year,
    COUNT(*) AS cnt
FROM obrs
WHERE deleted = 0
GROUP BY year
ORDER BY year;

--Нагрузка по лабораториям за все время 
SELECT 
    p.name AS lab_name,
    COUNT(*) AS results_cnt
FROM results r
JOIN podrs p ON p.id = r.podr_id
WHERE r.deleted = 0
GROUP BY HEX(p.name)
ORDER BY results_cnt DESC;

--По типам исследований за все время 
SELECT 
    YEAR(o.created) AS yr,
    ot.name AS obr_type,
    COUNT(*) AS cnt
FROM obrs o
JOIN obr_types ot ON ot.id = o.obr_type_id
WHERE o.deleted = 0
GROUP BY 1, HEX(ot.name)
ORDER BY 1, cnt DESC;

--Объекты (по количеству образцов)

-- 4. Объекты (по количеству образцов)
SELECT 
    ro.name AS object_name,
    COUNT(o.id) AS obrs_cnt
FROM obrs o
JOIN naprs n ON n.id = o.napr_id
JOIN resobjects ro ON ro.id = n.resobject_id
WHERE o.deleted = 0
GROUP BY HEX(ro.name)
ORDER BY obrs_cnt DESC;


-- Санитарные врачи — сколько отобрали (по количеству ОБРАЗЦОВ)
SELECT 
    sd.name AS doctor,
    COUNT(o.id) AS obrs_cnt
FROM naprs n
JOIN sandoctors sd ON sd.id = n.sandoctor_id
JOIN obrs o ON o.napr_id = n.id
WHERE n.deleted = 0
  AND o.deleted = 0
GROUP BY HEX(sd.name)
ORDER BY obrs_cnt DESC;

--Загрузка лабораторий по дням недели
SELECT 
    p.name AS lab_name,
    DAYNAME(r.created) AS day_of_week,
    COUNT(*) AS cnt
FROM results r
JOIN podrs p ON p.id = r.podr_id
WHERE r.deleted = 0
GROUP BY HEX(p.name), day_of_week, DAYOFWEEK(r.created)
ORDER BY lab_name, DAYOFWEEK(r.created);

--Работа в выходные дни — кто выпускает результаты
-- 1. Работа в выходные дни — кто выпускает результаты
SELECT 
    u.full_name AS full_name,
    DAYNAME(r.time_out) AS day_of_week,
    COUNT(*) AS cnt
FROM results r
JOIN users u ON u.id = r.user_id
WHERE r.deleted = 0
    AND r.time_out IS NOT NULL
    AND DAYOFWEEK(r.time_out) IN (1, 7)
    [[AND r.time_out >= {{start_date}}]]
    [[AND r.time_out <= {{end_date}}]]
GROUP BY HEX(u.full_name), day_of_week
ORDER BY cnt DESC;
