; Файл: lisp_helpers/bridge.lsp
; Описание:
;  Обработчик одиночного запроса от Python.
;  Команда ATC_PROCESS_REQUEST читает request.json и формирует response.json.
;
; ВАЖНО: файл сохраните в ANSI (Windows-1251/1252), не в UTF-8 with BOM.
(vl-load-com)

(defun atc-log (s)
  (princ (strcat "\n[ATC-Bridge] " s))
)

(defun atc-read-file-line (fname / f data)
  (if (findfile fname)
    (progn
      (setq f (open fname "r"))
      (setq data (read-line f))
      (close f)
      data
    )
    nil
  )
)

(defun atc-write-file-line (fname line / f)
  (setq f (open fname "w"))
  (if f
    (progn (write-line line f) (close f) t)
    nil
  )
)

(defun c:ATC_PROCESS_REQUEST ( / base reqFile respFile reqData cmd)
  ;; Параметры: тут жёстко прописан путь к папке проекта (скорее всего E:\AT-CAD\)
  (setq base "E:\\AT-CAD\\")
  (setq reqFile  (strcat base "lisp_bridge\\request.json"))   ; входной запрос от Python
  (setq respFile (strcat base "lisp_bridge\\response.json"))  ; выходной ответ для Python

  (atc-log (strcat "Processing request: " reqFile))
  (setq reqData (atc-read-file-line reqFile))
  (if (not reqData)
    (progn
      (atc-log "Request file not found or empty.")
      (princ)
    )
    (progn
      ;; ожидаемый формат прост — JSON с полем "command"
      ;; сделаем простую проверку текста для команд "get_point" / "get_entity"
      (cond
        ((vl-string-search "get_point" reqData)
         (atc-log "Command = get_point -> выдаём запрос точки (DE подсказка).")
         ;; напрямую запросим точку (на немецком)
         (setq pt (getpoint "\nWahlen Sie einen Punkt: "))
         (if pt
           (progn
             (atc-write-file-line respFile (strcat "{\"point\": [" (rtos (car pt) 2 6)
                                                   ", " (rtos (cadr pt) 2 6) ", " (rtos (caddr pt) 2 6) "]}"))
             (atc-log "Point written to response.json")
           )
           (progn
             (atc-write-file-line respFile "{\"cancelled\": true}")
             (atc-log "Point selection cancelled")
           )
         )
        )
        ((vl-string-search "get_entity" reqData)
         (atc-log "Command = get_entity -> запрашиваем выбор объекта (DE подсказка).")
         (setq sel (entsel "\nWahlen Sie ein Objekt: "))
         (if sel
           (progn
             (setq ename (car sel))
             (setq entdata (entget ename))
(setq handle (cdr (assoc 5 entdata)))
(setq layer  (cdr (assoc 8 entdata)))

;; Экранируем кавычки и обратные слэши вручную (примитивно, но надёжно)
(defun atc-escape-json (s)
  (if s
    (vl-string-subst "\\\"" "\"" (vl-string-subst "\\\\" "\\" s))
    ""
  )
)

(setq layerEsc (atc-escape-json layer))
(atc-write-file-line respFile
  (strcat "{\"entity\": {\"handle\":\"" handle "\", \"layer\":\"" layerEsc "\"}}")
)
(atc-log "Entity written to response.json")
           )
           (progn
             (atc-write-file-line respFile "{\"cancelled\": true}")
             (atc-log "Entity selection cancelled")
           )
         )
        )
        (t
         (atc-log "Unknown command in request.json")
         (atc-write-file-line respFile "{\"error\": \"unknown command\"}")
        )
      )
      ;; удаляем запрос чтобы не обрабатывать снова
      (if (findfile reqFile) (vl-file-delete reqFile))
    )
  )
  (princ)
)
