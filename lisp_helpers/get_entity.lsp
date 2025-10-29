; Файл: lisp_helpers/get_entity.lsp
; Описание:
; Позволяет выбрать любой объект и вернуть Python информацию об объекте:
; тип, слой, хэндл, координаты.
;
; Рус: "Выберите объект:"
; Нем: "Wählen Sie ein Objekt:"
; Англ: "Select object:"

(defun c:PY_GET_ENTITY ( / reqFile resFile entData entName entLayer entHandle f )
  (setq reqFile (findfile "programs/../lisp_bridge/request.json"))
  (setq resFile (findfile "programs/../lisp_bridge/response.json"))

  (setq entData (entsel "\nВыберите объект: "))
  (if entData
    (progn
      (setq entName (car entData))
      (setq entLayer (cdr (assoc 8 (entget entName))))
      (setq entHandle (cdr (assoc 5 (entget entName))))

      (setq f (open resFile "w"))
      (write-line
        (strcat "{\"entity\": {"
                "\"handle\": \"" entHandle "\", "
                "\"layer\": \"" entLayer "\"}}")
        f)
      (close f)
    )
    (progn
      (setq f (open resFile "w"))
      (write-line "{\"cancelled\": true}" f)
      (close f)
    )
  )
  (princ)
)
