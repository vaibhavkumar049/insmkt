from flask import render_template, flash, redirect, url_for, request, g, send_from_directory
from app import db
from app.ranking.forms import RankingForm
from flask_login import current_user, login_required
from app.models import Company, Indicator, Financial, Financial_per_month            
from datetime import datetime
from flask import send_from_directory
from app.ranking import bp
from app.universal_routes import before_request_u, required_roles_u, save_to_log, \
                                is_id_in_arr, get_hint, save_to_excel, \
                                transform_check_dates, str_to_bool, str_to_date
from app.transform_data import get_df_financial_per_period, get_df_financial_at_date, \
                                convert_df_to_list, merge_two_df_convert_to_list, \
                                merge_claims_prems_compute_LR
from app.plot_graphs import plot_scatter
import pandas as pd


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def get_info_for_ranking(b,e,show_last_year,b_l_y,e_l_y):#вспомогательная функция - получаем данные для ранкинга    
    net_premiums_total_l_y=None
    equity_total_l_y=None
    net_income_total_l_y=None
    solvency_margin_av_l_y=None
    net_claims_total_l_y=None
    lr_av_l_y=None

    ############################################################################
    #net premiums per period
    net_premiums = list()
    ind_name = 'net_premiums'
    df_net_premiums,net_premiums_total=get_df_financial_per_period(ind_name,b,e)
    if show_last_year:
        df_net_premiums_l_y,net_premiums_total_l_y=get_df_financial_per_period(ind_name,b_l_y,e_l_y)
        net_premiums = merge_two_df_convert_to_list(df_net_premiums,df_net_premiums_l_y,False,False,False,False)
    else:
        net_premiums = convert_df_to_list(df_net_premiums,False,False,False)

    ##########################################################################
    #equity at date
    equity = list()
    ind_name = 'equity'
    df_equity,equity_total = get_df_financial_at_date(ind_name,e)
    if show_last_year:
        df_equity_l_y,equity_total_l_y=get_df_financial_at_date(ind_name,e_l_y)
        equity = merge_two_df_convert_to_list(df_equity,df_equity_l_y,False,False,False,False)
    else:
        equity = convert_df_to_list(df_equity,False,False,False)
        
    #########################################################################
    #net income per period
    netincome = list()
    ind_name = 'net_income'
    df_net_income,net_income_total=get_df_financial_per_period(ind_name,b,e)
    if show_last_year:
        df_net_income_l_y,net_income_total_l_y=get_df_financial_per_period(ind_name,b_l_y,e_l_y)
        netincome = merge_two_df_convert_to_list(df_net_income,df_net_income_l_y,False,False,False,False)
    else:
        netincome = convert_df_to_list(df_net_income,False,False,False)

    ##############################################################################
    #solvency margin at date
    solvency_margin = list()
    ind_name = 'solvency_margin'
    df_sm,sm_total = get_df_financial_at_date(ind_name,e)
    solvency_margin_av = round(sm_total / df_sm.shape[0] ,2)
    if show_last_year:
        df_sm_l_y,sm_total_l_y=get_df_financial_at_date(ind_name,e_l_y)
        solvency_margin_av_l_y = round(sm_total_l_y / df_sm_l_y.shape[0] ,2)
        solvency_margin = merge_two_df_convert_to_list(df_sm,df_sm_l_y,True,False,False,False)
    else:
        solvency_margin = convert_df_to_list(df_sm,False,False,False)
    
    #################################################################################
    #net claims per period
    net_claims = list()
    ind_name = 'net_claims'
    df_net_claims,net_claims_total=get_df_financial_per_period(ind_name,b,e)
    if show_last_year:
        df_net_claims_l_y,net_claims_total_l_y=get_df_financial_per_period(ind_name,b_l_y,e_l_y)
        net_claims = merge_two_df_convert_to_list(df_net_claims,df_net_claims_l_y,False,False,False,False)
    else:
        net_claims = convert_df_to_list(df_net_claims,False,False,False)

    ###########################################################################
    #net Loss Ratio per period
    
    lr_list = list()
    ind_name_claims = 'net_claims'
    ind_name_premiums = 'net_premiums'
    df_net_claims,net_claims_total=get_df_financial_per_period(ind_name_claims,b,e)
    df_net_premiums,net_premiums_total=get_df_financial_per_period(ind_name_premiums,b,e)    
    df_lr,lr_av = merge_claims_prems_compute_LR(df_net_claims,df_net_premiums,False,False)   
    
    if show_last_year:
        df_net_claims_l_y,net_claims_total_l_y=get_df_financial_per_period(ind_name_claims,b_l_y,e_l_y)
        df_net_premiums_l_y,net_premiums_total_l_y=get_df_financial_per_period(ind_name_premiums,b_l_y,e_l_y)
        df_lr_l_y,lr_av_l_y = merge_claims_prems_compute_LR(df_net_claims_l_y,df_net_premiums_l_y,False,False)        
        lr_list = merge_two_df_convert_to_list(df_lr,df_lr_l_y,True,True,False,False)
    else:
        lr_list = convert_df_to_list(df_lr,True,False,False)

    return net_premiums, equity, netincome, solvency_margin, net_claims, lr_list, \
        net_premiums_total, equity_total, net_income_total, solvency_margin_av, net_claims_total, lr_av, \
        net_premiums_total_l_y, equity_total_l_y, net_income_total_l_y, solvency_margin_av_l_y, net_claims_total_l_y, lr_av_l_y


def get_data_for_plot(ind_name,top_equity,annotate,b,e):#helpier function
    if annotate:
        labels = list()
    else:
        labels = None
    _x = list()
    _y = list()

    df_equity,equity_total = get_df_financial_at_date('equity',e)
    df_indicator,indicator_total = get_df_financial_per_period(ind_name,b,e)
        
    df_merged = pd.merge(df_equity,df_indicator,on='id')
    df_merged.rename(columns = {'alias_x':'alias','value_x':'equity','value_y':'value'}, inplace = True)#rename columns

    if top_equity:#top equity companaies
        is_eq_share = df_merged['share_x'] >= 10#filter those companies w/ share of equaty 10% +
    else:#not top equity companies
        is_eq_share = df_merged['share_x'] < 10#filter those companies w/ share of equaty less than 10%

    df_merged_final = df_merged[is_eq_share]#filter rows
    df_merged_final = df_merged_final.drop(['alias_y','share_x','share_y','id'], axis=1)#drop columns

    if not df_merged_final.empty:
        for row_index,row in df_merged_final.iterrows():
            _x.append(row.equity/1000000)
            _y.append(row.value/1000000)
            if annotate:            
                labels.append(row.alias)

    return _x,_y,labels


@bp.route('/chart.png/<b>/<e>/<b_l_y>/<e_l_y>/<show_last_year_str>/<annotate_param>/<chart_type>/<indicator_type>/<top_equity_str>')#plot chart for a given class
def plot_png(b,e,b_l_y,e_l_y,show_last_year_str,annotate_param,chart_type,indicator_type,top_equity_str):
    show_last_year = str_to_bool(show_last_year_str)
    top_equity = str_to_bool(top_equity_str)
    annotate = str_to_bool(annotate_param)
    b = str_to_date(b)
    e = str_to_date(e)
    b_l_y = str_to_date(b_l_y)
    e_l_y = str_to_date(e_l_y)
    xlabel = 'Собственный капитал, млрд.тг.'
    ylabel = None
    title = None
    label1 = 'текущий период'
    label2 = 'прошлый год'

    if chart_type == 'scatter':
        if indicator_type == 'net_prems_equity':
            title = 'Чистые премии vs. Собственный капитал'
            ylabel = 'Чистые премии, млрд.тг.'
            _x,_y,labels = get_data_for_plot('net_premiums',top_equity,annotate,b,e)
        elif indicator_type == 'net_income_equity':
            title = 'Прибыль vs. Собственный капитал'
            ylabel = 'Прибыль, млрд.тг.'
            _x,_y,labels = get_data_for_plot('net_income',top_equity,annotate,b,e)

        return plot_scatter(_x,_y,title,labels,xlabel,ylabel)
    

def path_to_charts(base_img_path,b,e,b_l_y,e_l_y,show_last_year,annotate,chart_type,indicator_type,top_equity):#путь к графику
    path = "/" + base_img_path + "/" + b.strftime('%m-%d-%Y') + "/" + e.strftime('%m-%d-%Y')\
             + "/" + b_l_y.strftime('%m-%d-%Y') + "/" + e_l_y.strftime('%m-%d-%Y') + "/" + str(show_last_year)\
                 + "/" + str(annotate) + "/" + chart_type + "/" + indicator_type + "/" + str(top_equity)
    return path


@bp.route('/ranking',methods=['GET','POST'])#ранкинг, обзор рынка
@login_required
def ranking():
    form = RankingForm()
    b = g.min_report_date
    e = g.last_report_date
    net_premiums = None
    net_premiums_total = None
    net_claims = None
    net_claims_total = None
    equity = None
    equity_total = None    
    netincome = None
    net_income_total = None    
    solvency_margin = None
    solvency_margin_av = None
    lr_list = None
    lr_av = None    
    show_last_year = False    
    net_premiums_total_l_y = None
    equity_total_l_y = None
    net_income_total_l_y = None
    solvency_margin_av_l_y = None
    net_claims_total_l_y = None
    lr_av_l_y = None
    b_l_y = None
    e_l_y = None
    show_info = False
    solvency_margin_av_change = None
    img_path_net_prems_eq_1 = None
    img_path_net_prems_eq_2 = None
    img_path_net_income_eq_1 = None
    img_path_net_income_eq_2 = None


    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date

    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        show_last_year = form.show_last_year.data
        #преобразуем даты выборки (сбросим на 1-е число) и проверим корректность ввода
        b,e,b_l_y,e_l_y,period_str,check_res,err_txt = transform_check_dates(form.begin_d.data,form.end_d.data,show_last_year)
        if not check_res:
            flash(err_txt)
            return redirect(url_for('ranking.ranking'))
        try:
            net_premiums, equity, netincome, solvency_margin, net_claims, lr_list, \
                net_premiums_total, equity_total, net_income_total, solvency_margin_av, net_claims_total, lr_av, \
                net_premiums_total_l_y, equity_total_l_y, net_income_total_l_y, solvency_margin_av_l_y, \
                net_claims_total_l_y, lr_av_l_y = get_info_for_ranking(b,e,show_last_year,b_l_y,e_l_y)#рассчитаем показатели                
        except:
            flash('Не могу получить данные за текущий или прошлый период. Проверьте период.')
            return redirect(url_for('ranking.ranking'))
        try:
            solvency_margin_av_change = round(solvency_margin_av-solvency_margin_av_l_y,1)
        except:
            solvency_margin_av_change = None
        #scatters
        base_name = 'chart.png'
        img_path_net_prems_eq_1 = path_to_charts(base_name,b,e,b_l_y,e_l_y,show_last_year,True,'scatter','net_prems_equity',True)
        img_path_net_prems_eq_2 = path_to_charts(base_name,b,e,b_l_y,e_l_y,show_last_year,True,'scatter','net_prems_equity',False)
        img_path_net_income_eq_1 = path_to_charts(base_name,b,e,b_l_y,e_l_y,show_last_year,True,'scatter','net_income_equity',True)
        img_path_net_income_eq_2 = path_to_charts(base_name,b,e,b_l_y,e_l_y,show_last_year,True,'scatter','net_income_equity',False)
        
        if form.show_info_submit.data:#show data
            save_to_log('ranking',current_user.id)
            show_info = True
        elif form.save_to_file_submit.data:
            save_to_log('ranking_file',current_user.id)
            sheets = list()
            sheets_names = list()            
            sheets.append(net_premiums)
            sheets.append(equity)
            sheets.append(netincome)
            sheets.append(solvency_margin)
            sheets.append(lr_list)
            sheets_names.append(period_str + ' чист. премии')
            sheets_names.append(period_str + ' капитал')
            sheets_names.append(period_str + ' прибыль')
            sheets_names.append(period_str + ' ФМП')
            sheets_names.append(period_str + ' коэф. выплат')
            wb_name = 'ranking_' + period_str
            path, wb_name_f = save_to_excel('ranking',period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('ranking/ranking.html', round=round,get_hint=get_hint,\
                    form=form, show_info=show_info, b=b, e=e, show_last_year=show_last_year,b_l_y=b_l_y,e_l_y=e_l_y, \
                    net_premiums=net_premiums, net_premiums_total=net_premiums_total, \
                    net_claims=net_claims, net_claims_total=net_claims_total, \
                    equity=equity,  equity_total=equity_total,\
                    netincome=netincome, net_income_total=net_income_total, \
                    solvency_margin=solvency_margin, solvency_margin_av=solvency_margin_av, \
                    lr_list=lr_list,  lr_av=lr_av, \
                    net_premiums_total_l_y=net_premiums_total_l_y, \
                    net_claims_total_l_y=net_claims_total_l_y, \
                    equity_total_l_y=equity_total_l_y, \
                    net_income_total_l_y=net_income_total_l_y, \
                    solvency_margin_av_l_y=solvency_margin_av_l_y, \
                    lr_av_l_y=lr_av_l_y, \
                    solvency_margin_av_change=solvency_margin_av_change, \
                    img_path_net_prems_eq_1=img_path_net_prems_eq_1, img_path_net_prems_eq_2=img_path_net_prems_eq_2, \
                    img_path_net_income_eq_1=img_path_net_income_eq_1, img_path_net_income_eq_2=img_path_net_income_eq_2)
