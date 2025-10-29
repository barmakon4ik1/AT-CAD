; Файл: lisp_helpers/get_point.lsp
; Описание:
; Получает точку от пользователя и сохраняет результат в JSON-файл для Python.
; Работает как часть моста Python ↔ AutoLISP.
;
; Рус: "Укажите точку:"
; Нем: "Geben Sie einen Punkt an:"
; Англ: "Specify point:"

(defun c:PY_GET_POINT ( / reqFile resFile reqData prompt pt f )
  (setq reqFile (findfile "programs/../lisp_bridge/request.json"))
  (setq resFile (findfile "programs/../lisp_bridge/response.json"))

  (if (and reqFile (findfile reqFile))
    (progn
      (setq f (open reqFile "r"))
      (setq reqData (read-line f))
      (close f)
      (setq prompt (vl-string-trim "\"" (vl-string-subst "" "{" reqData))) ; упрощённо
    )
  )

  (if (not prompt)
    (setq prompt "Укажите точку: ")
  )

  (setq pt (getpoint prompt))
  (if pt
    (progn
      (setq f (open resFile "w"))
      (write-line
        (strcat "{\"point\": [" (rtos (car pt) 2 3) ", "
                             (rtos (cadr pt) 2 3) ", "
                             (rtos (caddr pt) 2 3) "]}")
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
