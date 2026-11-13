# ============================================================================
# ФУНКЦИЯ ДЛЯ ШАГА 6 (step6/src/impl/main.py)
#
# 1) Вставьте метод fill_forecast_year_ifrs ниже внутрь класса Model
#    (отступ 4 пробела, рядом с другими методами: unify_types и т.д.).
#
# 2) Вызовите его в data_mapper сразу после унификации типов:
#
#        current_df = self.unify_types(current_df)
#        current_df = self.fill_forecast_year_ifrs(current_df, current_date)   # <-- добавить
#        df = current_df.copy()
#
#    (это место после строки "current_df = self.unify_types(current_df)",
#     перед "df = current_df.copy()", до add_ac_fc_detalization / aggregate_data_to_segment)
#
# Нужны только pandas как pd (в step6 уже импортирован).
# ============================================================================

    def fill_forecast_year_ifrs(self, df, current_date):
        """
        Досчитывает для прогнозных дат (DATE_ON > current_date) накопленное
        досоздание (восстановление) резерва по МСФО с начала года:
            COR_BAL_YEAR_IFRS  = PROV_BAL_IFRS  - PROV_BAL_IFRS  на конец прошлого года
            COR_OFFB_YEAR_IFRS = PROV_OFFB_IFRS - PROV_OFFB_IFRS на конец прошлого года
        Свертка и списания в прогнозе равны 0, поэтому в формулу не входят.
        Остатки на конец прошлого года берутся из факта (а если конец прошлого
        года тоже прогнозный - из прогноза). Фактические строки не меняются.
        """
        keys = ['SEGMENT', 'SEGMENT_REPORT', 'FV_FLAG']
        df = df.copy()
        cur = pd.Timestamp(current_date)

        # Остатки резерва на каждую дату в разрезе ключей
        # (суммируем по POCI_FLAG и STAGE, т.к. в прогнозе они равны 0)
        stock = (
            df.groupby(['DATE_ON'] + keys, dropna=False, as_index=False)
              [['PROV_BAL_IFRS', 'PROV_OFFB_IFRS']].sum()
              .rename(columns={
                  'DATE_ON': 'PREV_YEAR_DATE',
                  'PROV_BAL_IFRS': 'PROV_BAL_IFRS_PY',
                  'PROV_OFFB_IFRS': 'PROV_OFFB_IFRS_PY',
              })
        )

        # Конец прошлого года для каждой строки
        df['PREV_YEAR_DATE'] = df['DATE_ON'] - pd.offsets.YearEnd(1)
        df = df.merge(stock, on=['PREV_YEAR_DATE'] + keys, how='left')

        is_forecast = df['DATE_ON'] > cur

        # Баланс
        mask_bal = is_forecast & df['PROV_BAL_IFRS_PY'].notna()
        df.loc[mask_bal, 'COR_BAL_YEAR_IFRS'] = (
            df.loc[mask_bal, 'PROV_BAL_IFRS'] - df.loc[mask_bal, 'PROV_BAL_IFRS_PY']
        )

        # Внебаланс
        mask_offb = is_forecast & df['PROV_OFFB_IFRS_PY'].notna()
        df.loc[mask_offb, 'COR_OFFB_YEAR_IFRS'] = (
            df.loc[mask_offb, 'PROV_OFFB_IFRS'] - df.loc[mask_offb, 'PROV_OFFB_IFRS_PY']
        )

        not_filled = int((is_forecast & ~mask_bal).sum())
        print(f"COR_*_YEAR_IFRS для прогноза: заполнено {int(mask_bal.sum())} строк, "
              f"без остатка на конец прошлого года (оставлен 0): {not_filled}")

        return df.drop(columns=['PREV_YEAR_DATE', 'PROV_BAL_IFRS_PY', 'PROV_OFFB_IFRS_PY'])
